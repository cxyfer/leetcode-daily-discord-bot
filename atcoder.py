import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from utils.config import get_config
from utils.database import ProblemsDatabaseManager
from utils.logger import get_leetcode_logger

logger = get_leetcode_logger()

USER_AGENT = "LeetCodeDailyDiscordBot/1.0"


class AtCoderClient:
    KENKOOOO_PROBLEMS_URL = "https://kenkoooo.com/atcoder/resources/problems.json"
    CONTEST_ARCHIVE_URL = "https://atcoder.jp/contests/archive"
    CONTEST_TASKS_URL_TEMPLATE = "https://atcoder.jp/contests/{contest_id}/tasks"
    PROBLEM_URL_TEMPLATE = "https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}"

    def __init__(
        self,
        data_dir: str = "data",
        db_path: str = "data/data.db",
        rate_limit: float = 1.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        max_backoff: float = 30.0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.data_dir / "atcoder_progress.json"
        self.problems_db = ProblemsDatabaseManager(db_path)
        self.rate_limit = max(rate_limit, 1.0)
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_backoff = max_backoff
        self._last_request_at = 0.0

    def _headers(self) -> dict:
        return {"User-Agent": USER_AGENT}

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_for = self.rate_limit - elapsed
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_request_at = time.monotonic()

    async def _fetch_text(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        for attempt in range(1, self.max_retries + 1):
            await self._throttle()
            try:
                async with session.get(url, headers=self._headers()) as response:
                    if response.status == 429:
                        backoff = min(self.max_backoff, self.backoff_base * (2 ** (attempt - 1)))
                        logger.warning("Rate limited (%s). Backing off %.1fs", url, backoff)
                        await asyncio.sleep(backoff)
                        continue
                    if response.status >= 400:
                        logger.warning("HTTP %s while fetching %s", response.status, url)
                        return None
                    return await response.text()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt >= self.max_retries:
                    logger.error("Failed to fetch %s: %s", url, exc)
                    return None
                backoff = min(self.max_backoff, self.backoff_base * (2 ** (attempt - 1)))
                logger.warning("Fetch failed (%s), retry in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
        return None

    def _parse_contest_archive(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        contest_ids: list[str] = []
        seen = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not href.startswith("/contests/"):
                continue
            if "/tasks" in href or "/archive" in href:
                continue
            contest_id = href.replace("/contests/", "").strip("/")
            if not contest_id or contest_id in seen:
                continue
            contest_ids.append(contest_id)
            seen.add(contest_id)
        return contest_ids

    def _parse_contest_tasks(self, html: str, contest_id: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return []
        problems: list[dict] = []
        seen = set()
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            index_text = cols[0].get_text(strip=True)
            link = cols[1].find("a")
            if not link or not link.get("href"):
                continue
            href = link["href"]
            if f"/contests/{contest_id}/tasks/" not in href:
                continue
            problem_id = href.split("/tasks/")[-1].split("/")[0]
            if not problem_id or problem_id in seen:
                continue
            title_text = link.get_text(strip=True)
            if " - " in title_text:
                title_text = title_text.split(" - ", 1)[1]
            problems.append(
                {
                    "id": problem_id,
                    "source": "atcoder",
                    "slug": problem_id,
                    "title": title_text,
                    "title_cn": "",
                    "difficulty": None,
                    "ac_rate": None,
                    "rating": None,
                    "contest": contest_id,
                    "problem_index": index_text,
                    "tags": None,
                    "link": self.PROBLEM_URL_TEMPLATE.format(
                        contest_id=contest_id, problem_id=problem_id
                    ),
                    "category": "Algorithms",
                    "paid_only": 0,
                    "content": None,
                    "content_cn": None,
                    "similar_questions": None,
                }
            )
            seen.add(problem_id)
        return problems

    def _extract_statement(self, html: str, prefer_lang: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        lang_selector = f"span.lang-{prefer_lang}"
        statement = soup.select_one(lang_selector)
        if statement:
            return str(statement)
        if prefer_lang != "en":
            fallback = soup.select_one("span.lang-ja")
            if fallback:
                return str(fallback)
            container = soup.find(id="task-statement")
            if container:
                return str(container)
        return None

    def _is_permission_denied(self, html: str) -> bool:
        lowered = html.lower()
        return (
            "permission denied" in lowered
            or "access denied" in lowered
            or "sign in" in lowered
            or "login" in lowered
        )

    def _build_problem_from_kenkoooo(self, item: dict) -> Optional[dict]:
        problem_id = item.get("id") or item.get("problem_id")
        if not problem_id:
            return None
        contest_id = item.get("contest_id") or problem_id.split("_")[0]
        title = item.get("title") or item.get("name") or ""
        return {
            "id": problem_id,
            "source": "atcoder",
            "slug": problem_id,
            "title": title,
            "title_cn": "",
            "difficulty": None,
            "ac_rate": None,
            "rating": None,
            "contest": contest_id,
            "problem_index": item.get("problem_index"),
            "tags": None,
            "link": self.PROBLEM_URL_TEMPLATE.format(
                contest_id=contest_id, problem_id=problem_id
            ),
            "category": "Algorithms",
            "paid_only": 0,
            "content": None,
            "content_cn": None,
            "similar_questions": None,
        }

    async def fetch_from_kenkoooo(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            text = await self._fetch_text(session, self.KENKOOOO_PROBLEMS_URL)
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Kenkoooo response")
            return []
        problems: list[dict] = []
        for item in data:
            problem = self._build_problem_from_kenkoooo(item)
            if problem:
                problems.append(problem)
        if problems:
            self.problems_db.update_problems(problems)
        logger.info("Kenkoooo sync completed: %s problems", len(problems))
        return problems

    async def fetch_contest_list(self, pages: Optional[int] = None) -> list[str]:
        contests: list[str] = []
        page = 1
        async with aiohttp.ClientSession() as session:
            while True:
                if pages is not None and page > pages:
                    break
                url = self.CONTEST_ARCHIVE_URL
                if page > 1:
                    url = f"{self.CONTEST_ARCHIVE_URL}?page={page}"
                html = await self._fetch_text(session, url)
                if not html:
                    break
                page_contests = self._parse_contest_archive(html)
                if not page_contests:
                    break
                for contest_id in page_contests:
                    if contest_id not in contests:
                        contests.append(contest_id)
                page += 1
        logger.info("Fetched %s contests", len(contests))
        return contests

    async def fetch_contest_problems(
        self, contest_id: str, session: aiohttp.ClientSession
    ) -> list[dict]:
        url = self.CONTEST_TASKS_URL_TEMPLATE.format(contest_id=contest_id)
        html = await self._fetch_text(session, url)
        if not html:
            return []
        return self._parse_contest_tasks(html, contest_id)

    async def fetch_problem_content(
        self, session: aiohttp.ClientSession, contest_id: str, problem_id: str
    ) -> Optional[str]:
        base_url = self.PROBLEM_URL_TEMPLATE.format(
            contest_id=contest_id, problem_id=problem_id
        )
        html = await self._fetch_text(session, f"{base_url}?lang=en")
        if not html:
            return None
        if self._is_permission_denied(html):
            logger.warning("Permission denied while fetching %s", base_url)
            return None
        content = self._extract_statement(html, prefer_lang="en")
        if content:
            return content
        html = await self._fetch_text(session, f"{base_url}?lang=ja")
        if not html:
            return None
        if self._is_permission_denied(html):
            logger.warning("Permission denied while fetching %s", base_url)
            return None
        return self._extract_statement(html, prefer_lang="ja")

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
        fetched.add(contest_id)
        progress["fetched_contests"] = sorted(fetched)
        progress["last_contest_id"] = contest_id
        progress["last_updated"] = datetime.now(timezone.utc).isoformat()
        with self.progress_file.open("w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, sort_keys=True)

    async def fetch_single_contest(self, contest_id: str) -> int:
        async with aiohttp.ClientSession() as session:
            problems = await self.fetch_contest_problems(contest_id, session)
            if not problems:
                return 0
            for problem in problems:
                content = await self.fetch_problem_content(
                    session, contest_id, problem["id"]
                )
                if content:
                    problem["content"] = content
                self.problems_db.update_problem(problem)
            return len(problems)

    async def fetch_all_problems(self, resume: bool = True) -> int:
        contests = await self.fetch_contest_list()
        progress = self.get_progress() if resume else {"fetched_contests": []}
        fetched = set(progress.get("fetched_contests", []))
        total = 0
        async with aiohttp.ClientSession() as session:
            for contest_id in contests:
                if contest_id in fetched:
                    continue
                problems = await self.fetch_contest_problems(contest_id, session)
                if not problems:
                    continue
                for problem in problems:
                    content = await self.fetch_problem_content(
                        session, contest_id, problem["id"]
                    )
                    if content:
                        problem["content"] = content
                    self.problems_db.update_problem(problem)
                total += len(problems)
                self.save_progress(contest_id)
        logger.info("Fetched %s problems", total)
        return total

    def show_status(self) -> None:
        progress = self.get_progress()
        fetched = progress.get("fetched_contests", [])
        logger.info(
            "Progress: %s contests fetched. last_contest_id=%s last_updated=%s",
            len(fetched),
            progress.get("last_contest_id"),
            progress.get("last_updated"),
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="AtCoder CLI tool")
    parser.add_argument("--sync-kenkoooo", action="store_true", help="Sync from Kenkoooo")
    parser.add_argument("--sync-history", action="store_true", help="Alias for --sync-kenkoooo")
    parser.add_argument("--fetch-all", action="store_true", help="Fetch all contests")
    parser.add_argument("--resume", action="store_true", help="Resume from progress file")
    parser.add_argument("--contest", type=str, help="Fetch a single contest")
    parser.add_argument("--status", action="store_true", help="Show progress status")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Rate limit in seconds")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")
    parser.add_argument("--db-path", type=str, default=None, help="Database path")

    args = parser.parse_args()
    config = get_config()
    data_dir = args.data_dir or "data"
    db_path = args.db_path or config.database_path

    client = AtCoderClient(
        data_dir=data_dir,
        db_path=db_path,
        rate_limit=args.rate_limit,
    )

    if not (
        args.sync_kenkoooo
        or args.sync_history
        or args.fetch_all
        or args.contest
        or args.status
    ):
        parser.print_help()
        return

    if args.status:
        client.show_status()

    if args.sync_kenkoooo or args.sync_history:
        await client.fetch_from_kenkoooo()

    if args.fetch_all:
        await client.fetch_all_problems(resume=args.resume)

    if args.contest:
        await client.fetch_single_contest(args.contest)


if __name__ == "__main__":
    asyncio.run(main())
