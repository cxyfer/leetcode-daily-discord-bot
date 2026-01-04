import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp

from utils.database import ProblemsDatabaseManager
from utils.logger import get_leetcode_logger

logger = get_leetcode_logger()

USER_AGENT = "LeetCodeDailyDiscordBot/1.0"
RATE_LIMIT_MARKERS = (
    "too many requests",
    "please wait",
    "captcha",
    "call limit exceeded",
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
        rate_limit: float = 2.0,
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
        self._last_request_at = 0.0

    def _headers(self, referer: Optional[str] = None) -> dict:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
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
        text = html.lower()
        if "/enter" in text:
            return True
        return any(marker in text for marker in RATE_LIMIT_MARKERS)

    async def _fetch_text(
        self,
        session: aiohttp.ClientSession,
        url: str,
        referer: Optional[str] = None,
    ) -> Optional[str]:
        for attempt in range(1, self.max_retries + 1):
            await self._throttle()
            try:
                async with session.get(url, headers=self._headers(referer)) as response:
                    if response.status in {429, 403, 503}:
                        backoff = min(
                            self.max_backoff, self.backoff_base * (2 ** (attempt - 1))
                        )
                        logger.warning("Rate limited (%s). Backing off %.1fs", url, backoff)
                        await asyncio.sleep(backoff)
                        continue
                    if response.status >= 400:
                        logger.warning("HTTP %s while fetching %s", response.status, url)
                        return None
                    text = await response.text()
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
                logger.warning("Rate limited by content (%s). Backing off %.1fs", url, backoff)
                await asyncio.sleep(backoff)
                continue
            return text
        return None

    async def _fetch_json(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[dict]:
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
        stats_map = {
            (item.get("contestId"), item.get("index")): item for item in stats or []
        }
        merged: list[dict] = []
        for problem in problems or []:
            key = (problem.get("contestId"), problem.get("index"))
            merged_problem = self._build_problem_from_api(problem, stats_map.get(key, {}))
            if merged_problem:
                merged.append(merged_problem)
        return merged

    async def sync_problemset(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            payload = await self._fetch_json(session, self.PROBLEMSET_API)
        if not payload:
            return []
        if payload.get("status") != "OK":
            logger.warning("Problemset API error: %s", payload.get("comment"))
            return []

        result = payload.get("result") or {}
        problems = self._merge_problemset(
            result.get("problems", []), result.get("problemStatistics", [])
        )
        if not problems:
            return []

        problems_for_insert = [
            {**problem, "tags": self._serialize_tags(problem.get("tags"))}
            for problem in problems
        ]
        inserted = self.problems_db.update_problems(problems_for_insert)
        logger.info(
            "Problemset sync: %s problems fetched, %s inserted, %s skipped (existing)",
            len(problems),
            inserted,
            len(problems) - inserted,
        )
        return problems

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
