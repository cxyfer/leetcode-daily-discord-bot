"""Similarity searcher for embedded problems."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from utils.database import EmbeddingDatabaseManager
from utils.logger import get_database_logger

from .storage import EmbeddingStorage

logger = get_database_logger()


class SimilaritySearcher:
    def __init__(self, db: EmbeddingDatabaseManager, storage: EmbeddingStorage):
        self.db = db
        self.storage = storage

    def _get_problem_info_sync(self, source: str, problem_id: str) -> Optional[dict]:
        row = self.db.execute(
            "SELECT id, title, difficulty, link FROM problems WHERE source = ? AND id = ?",
            (source, problem_id),
            fetchone=True,
        )
        if not row:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "difficulty": row[2],
            "link": row[3],
        }

    async def get_problem_info(self, source: str, problem_id: str) -> Optional[dict]:
        return await asyncio.to_thread(self._get_problem_info_sync, source, problem_id)

    async def search(
        self,
        query_embedding: List[float],
        source: Optional[str],
        top_k: int,
        min_similarity: float,
    ) -> List[dict]:
        results = await self.storage.search_similar(
            query_embedding, source, top_k, min_similarity
        )
        if not results:
            return []

        enriched: List[dict] = []
        for result in results:
            info = await self.get_problem_info(result["source"], result["problem_id"])
            if info:
                result.update(info)
            enriched.append(result)
        return enriched
