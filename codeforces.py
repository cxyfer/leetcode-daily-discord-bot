import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from utils.config import get_config
from utils.database import ProblemsDatabaseManager
from utils.logger import get_leetcode_logger

logger = get_leetcode_logger()

# 使用 curl_cffi 時，盡量減少手動標頭，讓 impersonate 自動處理
RATE_LIMIT_MARKERS = (
    "too many requests",
    "please wait",
    "captcha",
    "call limit exceeded",
    "attention required",
    "cloudflare",
)


class CodeforcesClient:
    API_BASE = "https://codeforces.com/api"
    PROBLEMSET_API = f"{API_BASE}/problemset.problems"
    CONTEST_LIST_API = f"{API_BASE}/contest.list"
    CONTEST_STANDINGS_API = f"{API_BASE}/contest.standings"
    PROBLEM_URL_TEMPLATE = "https://codeforces.com/contest/{contest_id}/problem/{index}"

    def __init__(
        self,
        data_dir: str = "data",
        db_path: str = "data/data.db",
        rate_limit: float = 3.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        max_backoff: float = 60.0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.data_dir / "codeforces_progress.json"
        self.problems_db = ProblemsDatabaseManager(db_path)
        self.rate_limit = max(rate_limit, 2.0)
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_backoff = max_backoff
        self._last_request_at = time.monotonic() - rate_limit

    def _headers(self, referer: Optional[str] = None) -> dict:
        # curl_cffi 的 impersonate 會處理大部分標頭
        headers = {}
        if referer:
            headers["Referer"] = referer
        return headers

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_for = self.rate_limit - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_request_at = time.monotonic()

    def _is_rate_limited(self, html: str) -> bool:
        if not html:
            return False

        # 如果能找到題目敘述，表示沒有被擋
        if "div.problem-statement" in html or 'class="problem-statement"' in html:
            return False

        text = html.lower()
        # 檢查標題是否為 Cloudflare 的特徵
        if "<title>attention required! | cloudflare</title>" in text:
            return True
        if "<title>just a moment...</title>" in text:
            return True

        # 只有在非常短的頁面中才檢查關鍵字，避免誤判
        if len(html) < 5000:
            if "/enter" in text:
                return True
            return any(marker in text for marker in RATE_LIMIT_MARKERS)

        return False

    async def _fetch_text(
        self,
        session: AsyncSession,
        url: str,
        referer: Optional[str] = None,
    ) -> Optional[str]:
        for attempt in range(1, self.max_retries + 1):
            await self._throttle()
            try:
                headers = self._headers(referer)
                # 使用 impersonate="chrome124" 模擬真實瀏覽器 TLS 指紋
                response = await session.get(url, headers=headers, timeout=30)

                if response.status_code in {429, 403, 503}:
                    backoff = min(self.max_backoff, self.backoff_base * (2 ** (attempt - 1)))
                    logger.warning(
                        "Blocked or Rate limited (%s, status=%s). Backing off %.1fs",
                        url,
                        response.status_code,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    logger.warning("HTTP %s while fetching %s", response.status_code, url)
                    return None

                text = response.text
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt >= self.max_retries:
                    logger.error("Failed to fetch %s: %s", url, exc)
                    return None
                backoff = min(self.max_backoff, self.backoff_base * (2 ** (attempt - 1)))
                logger.warning("Fetch failed (%s), retry in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                continue

            if self._is_rate_limited(text):
                backoff = min(self.max_backoff, self.backoff_base * (2 ** (attempt - 1)))
                logger.warning("Rate limited page content detected (%s). Backing off %.1fs", url, backoff)
                await asyncio.sleep(backoff)
                continue
            return text
        return None

    async def _fetch_json(self, session: AsyncSession, url: str) -> Optional[dict]:
        text = await self._fetch_text(session, url)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from %s: %s", url, exc)
            return None

    def _build_problem_from_api(self, problem: dict, stats: dict) -> Optional[dict]:
        contest_id = problem.get("contestId")
        index = problem.get("index")
        title = problem.get("name")
        if contest_id is None or not index or not title:
            return None
        slug = f"{contest_id}{index}"
        return {
            "id": slug,
            "source": "codeforces",
            "slug": slug,
            "title": title,
            "title_cn": "",
            "difficulty": None,
            "ac_rate": None,
            "rating": problem.get("rating"),
            "contest": str(contest_id),
            "problem_index": index,
            "tags": problem.get("tags", []),
            "link": self.PROBLEM_URL_TEMPLATE.format(contest_id=contest_id, index=index),
            "category": "Algorithms",
            "paid_only": 0,
            "content": None,
            "content_cn": None,
            "similar_questions": None,
        }

    def _serialize_tags(self, tags) -> str:
        if tags is None:
            return json.dumps([])
        if isinstance(tags, str):
            try:
                json.loads(tags)
                return tags
            except json.JSONDecodeError:
                return json.dumps([tags])
        return json.dumps(list(tags))

    def _merge_problemset(self, problems: list[dict], stats: list[dict]) -> list[dict]:
        stats_map = {(item.get("contestId"), item.get("index")): item for item in stats or []}
        merged: list[dict] = []
        for problem in problems or []:
            key = (problem.get("contestId"), problem.get("index"))
            merged_problem = self._build_problem_from_api(problem, stats_map.get(key, {}))
            if merged_problem:
                merged.append(merged_problem)
        return merged

    async def sync_problemset(self) -> list[dict]:
        async with AsyncSession(impersonate="chrome124") as session:
            payload = await self._fetch_json(session, self.PROBLEMSET_API)
        if not payload:
            return []
        if payload.get("status") != "OK":
            logger.warning("Problemset API error: %s", payload.get("comment"))
            return []

        result = payload.get("result") or {}
        problems = self._merge_problemset(result.get("problems", []), result.get("problemStatistics", []))
        if not problems:
            return []

        problems_for_insert = [{**problem, "tags": self._serialize_tags(problem.get("tags"))} for problem in problems]
        inserted = self.problems_db.update_problems(problems_for_insert)
        logger.info(
            "Problemset sync: %s problems fetched, %s inserted, %s skipped (existing)",
            len(problems),
            inserted,
            len(problems) - inserted,
        )
        return problems

    async def fetch_contest_list(self, include_gym: bool = False) -> list[int]:
        gym_flag = "true" if include_gym else "false"
        url = f"{self.CONTEST_LIST_API}?gym={gym_flag}"
        async with AsyncSession(impersonate="chrome124") as session:
            payload = await self._fetch_json(session, url)
        if not payload:
            return []
        if payload.get("status") != "OK":
            logger.warning("Contest list API error: %s", payload.get("comment"))
            return []

        contests = payload.get("result", [])
        finished = [contest for contest in contests if contest.get("phase") == "FINISHED"]
        filtered = finished
        if not include_gym:
            filtered = [contest for contest in finished if contest.get("type") != "GYM"]
        contest_ids = [contest.get("id") for contest in filtered if contest.get("id") is not None]
        contest_ids.sort(reverse=True)
        return contest_ids

    async def fetch_contest_problems(self, contest_id: int, session: AsyncSession) -> list[dict]:
        url = f"{self.CONTEST_STANDINGS_API}?contestId={contest_id}&from=1&count=1"
        payload = await self._fetch_json(session, url)
        if not payload:
            return []
        if payload.get("status") != "OK":
            logger.warning("Contest %s standings API error: %s", contest_id, payload.get("comment"))
            return []

        problems = (payload.get("result") or {}).get("problems", [])
        parsed: list[dict] = []
        for problem in problems:
            if problem.get("contestId") is None:
                problem = {**problem, "contestId": contest_id}
            built = self._build_problem_from_api(problem, {})
            if built:
                parsed.append(built)
        return parsed

    def _fix_relative_urls(self, html: str, base_url: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img", src=True):
            img["src"] = urljoin(base_url, img["src"])
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith(("#", "javascript:", "mailto:")):
                continue
            link["href"] = urljoin(base_url, href)
        return str(soup)

    def _extract_problem_statement(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        statement = soup.select_one("div.problem-statement")
        if not statement:
            return None
        return self._fix_relative_urls(str(statement), "https://codeforces.com")

    async def fetch_problem_content(self, session: AsyncSession, contest_id: int, index: str) -> Optional[str]:
        base_url = self.PROBLEM_URL_TEMPLATE.format(contest_id=contest_id, index=index)
        referer = f"https://codeforces.com/contest/{contest_id}"
        html = await self._fetch_text(session, f"{base_url}?locale=en", referer=referer)
        if not html:
            logger.warning("Empty content while fetching %s", base_url)
            return None
        content = self._extract_problem_statement(html)
        if not content:
            logger.warning("Problem statement missing for %s", base_url)
        return content

    async def fetch_content_by_url(self, session: AsyncSession, url: str) -> Optional[str]:
        separator = "&" if "?" in url else "?"
        html = await self._fetch_text(session, f"{url}{separator}locale=en", referer=url)
        if not html:
            return None
        if "/enter" in html.lower():
            logger.warning("Login required while fetching %s", url)
            return None
        content = self._extract_problem_statement(html)
        if not content:
            logger.warning("Problem statement missing for %s", url)
        return content

    async def fetch_single_contest(self, contest_id: int) -> int:
        async with AsyncSession(impersonate="chrome124") as session:
            problems = await self.fetch_contest_problems(contest_id, session)
            if not problems:
                return 0
            for problem in problems:
                content = await self.fetch_problem_content(session, contest_id, problem["problem_index"])
                if content:
                    problem["content"] = content
                self.problems_db.update_problem(problem)
            logger.info("Fetched contest %s: %s problems", contest_id, len(problems))
            return len(problems)

    async def fetch_all_problems(self, resume: bool = True, include_gym: bool = False) -> int:
        contests = await self.fetch_contest_list(include_gym=include_gym)
        progress = self.get_progress() if resume else {"fetched_contests": []}
        fetched = {str(contest_id) for contest_id in progress.get("fetched_contests", [])}
        remaining = [c for c in contests if str(c) not in fetched]
        logger.info(
            "Contest list: %s available, %s fetched, %s remaining",
            len(contests),
            len(fetched),
            len(remaining),
        )
        total = 0
        async with AsyncSession(impersonate="chrome124") as session:
            for contest_id in contests:
                if str(contest_id) in fetched:
                    continue
                problems = await self.fetch_contest_problems(contest_id, session)
                if not problems:
                    continue
                for problem in problems:
                    content = await self.fetch_problem_content(session, contest_id, problem["problem_index"])
                    if content:
                        problem["content"] = content
                    self.problems_db.update_problem(problem)
                total += len(problems)
                self.save_progress(contest_id)
                logger.info("Fetched contest %s: %s problems", contest_id, len(problems))
        logger.info("Total fetched: %s problems", total)
        return total

    async def fill_missing_content(self) -> int:
        missing = self.problems_db.get_problems_missing_content(source="codeforces")
        if not missing:
            logger.info("No problems missing content.")
            return 0

        total = len(missing)
        filled = 0
        logger.info("Fetching missing content for %s problems...", total)

        async with AsyncSession(impersonate="chrome124") as session:
            for index, (problem_id, link) in enumerate(missing, start=1):
                content = await self.fetch_content_by_url(session, link)
                if content:
                    self.problems_db.update_problem({"id": problem_id, "source": "codeforces", "content": content})
                    filled += 1
                if index % 50 == 0 or index == total:
                    logger.info("Processed %s/%s, filled %s", index, total, filled)
        return filled

    def show_status(self) -> None:
        progress = self.get_progress()
        fetched = progress.get("fetched_contests", [])
        missing = self.problems_db.count_missing_content(source="codeforces")
        logger.info(
            "Progress: %s contests fetched. last_contest_id=%s last_updated=%s",
            len(fetched),
            progress.get("last_contest_id"),
            progress.get("last_updated"),
        )
        logger.info("Missing content: %s", missing)

    def get_progress(self) -> dict:
        if not self.progress_file.exists():
            return {"fetched_contests": [], "last_updated": None, "last_contest_id": None}
        try:
            with self.progress_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to read progress file: %s", exc)
            return {"fetched_contests": [], "last_updated": None, "last_contest_id": None}

    def save_progress(self, contest_id: str) -> None:
        progress = self.get_progress()
        fetched = set(progress.get("fetched_contests", []))
        if contest_id is not None:
            fetched.add(str(contest_id))
        progress["fetched_contests"] = sorted(fetched)
        progress["last_contest_id"] = str(contest_id) if contest_id is not None else None
        progress["last_updated"] = datetime.now(timezone.utc).isoformat()

        tmp_path = self.progress_file.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            # 使用臨時檔原子寫入，避免損壞進度檔
            tmp_path.replace(self.progress_file)
        except Exception as exc:
            logger.warning("Failed to write progress file: %s", exc)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                logger.warning("Failed to cleanup temp progress file: %s", tmp_path)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Codeforces CLI tool")
    parser.add_argument(
        "--sync-problemset",
        action="store_true",
        help="Sync from Codeforces problemset API",
    )
    parser.add_argument("--fetch-all", action="store_true", help="Fetch all contests")
    parser.add_argument("--resume", action="store_true", help="Resume from progress file")
    parser.add_argument("--contest", type=int, help="Fetch a single contest by ID")
    parser.add_argument("--status", action="store_true", help="Show progress status")
    parser.add_argument(
        "--fill-missing-content",
        action="store_true",
        help="Fetch missing problem content",
    )
    parser.add_argument(
        "--missing-content-stats",
        action="store_true",
        help="Show missing content count",
    )
    parser.add_argument(
        "--missing-problems",
        action="store_true",
        help="Print IDs of problems missing content",
    )
    parser.add_argument(
        "--include-gym",
        action="store_true",
        help="Include gym contests in contest list",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Seconds between requests (default: 2.0)",
    )
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")
    parser.add_argument("--db-path", type=str, default=None, help="Database path")

    args = parser.parse_args()
    config = get_config()
    data_dir = args.data_dir or "data"
    db_path = args.db_path or config.database_path

    client = CodeforcesClient(
        data_dir=data_dir,
        db_path=db_path,
        rate_limit=args.rate_limit,
    )

    if not (
        args.sync_problemset
        or args.fetch_all
        or args.contest
        or args.status
        or args.fill_missing_content
        or args.missing_content_stats
        or args.missing_problems
    ):
        parser.print_help()
        return

    if args.status:
        client.show_status()

    if args.sync_problemset:
        await client.sync_problemset()

    if args.fetch_all:
        await client.fetch_all_problems(resume=args.resume, include_gym=args.include_gym)

    if args.contest:
        await client.fetch_single_contest(args.contest)

    if args.fill_missing_content:
        await client.fill_missing_content()

    if args.missing_content_stats:
        count = client.problems_db.count_missing_content(source="codeforces")
        print(f"Missing content: {count}")

    if args.missing_problems:
        missing = client.problems_db.get_problems_missing_content(source="codeforces")
        for problem_id, _ in missing:
            print(problem_id)


if __name__ == "__main__":
    asyncio.run(main())
