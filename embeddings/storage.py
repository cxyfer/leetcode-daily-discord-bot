"""Embedding storage backed by sqlite-vec."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Optional

from utils.database import EmbeddingDatabaseManager
from utils.logger import get_database_logger

logger = get_database_logger()


class EmbeddingStorage:
    def __init__(self, db: EmbeddingDatabaseManager):
        self.db = db

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_embedding_meta_sync(self, source: str, problem_id: str) -> Optional[dict]:
        row = self.db.execute(
            """
            SELECT source, problem_id, rewritten_content, model, dim, updated_at
            FROM problem_embeddings
            WHERE source = ? AND problem_id = ?
            """,
            (source, problem_id),
            fetchone=True,
        )
        if not row:
            return None
        return {
            "source": row[0],
            "problem_id": row[1],
            "rewritten_content": row[2],
            "model": row[3],
            "dim": row[4],
            "updated_at": row[5],
        }

    async def get_embedding_meta(self, source: str, problem_id: str) -> Optional[dict]:
        return await asyncio.to_thread(self._get_embedding_meta_sync, source, problem_id)

    def _get_vector_sync(self, source: str, problem_id: str) -> Optional[List[float]]:
        row = self.db.execute(
            "SELECT embedding FROM vec_embeddings WHERE source = ? AND problem_id = ?",
            (source, problem_id),
            fetchone=True,
        )
        if not row:
            return None
        return json.loads(row[0])

    async def get_vector(self, source: str, problem_id: str) -> Optional[List[float]]:
        return await asyncio.to_thread(self._get_vector_sync, source, problem_id)

    def _get_existing_ids_sync(self, source: str, model: str, dim: int) -> set[str]:
        rows = self.db.execute(
            """
            SELECT problem_id
            FROM problem_embeddings
            WHERE source = ? AND model = ? AND dim = ?
            """,
            (source, model, dim),
            fetchall=True,
        )
        return {row[0] for row in rows} if rows else set()

    async def get_existing_ids(self, source: str, model: str, dim: int) -> set[str]:
        return await asyncio.to_thread(self._get_existing_ids_sync, source, model, dim)

    def _get_existing_vector_ids_sync(self, source: str) -> set[str]:
        rows = self.db.execute(
            "SELECT problem_id FROM vec_embeddings WHERE source = ?",
            (source,),
            fetchall=True,
        )
        return {row[0] for row in rows} if rows else set()

    async def get_existing_vector_ids(self, source: str) -> set[str]:
        return await asyncio.to_thread(self._get_existing_vector_ids_sync, source)

    def _save_embedding_sync(
        self,
        source: str,
        problem_id: str,
        rewritten_content: str,
        model: str,
        dim: int,
        embedding: List[float],
    ) -> None:
        updated_at = self._now_iso()
        self.db.execute(
            "DELETE FROM vec_embeddings WHERE source = ? AND problem_id = ?",
            (source, problem_id),
            commit=True,
        )
        self.db.execute(
            "INSERT INTO vec_embeddings(source, problem_id, embedding) VALUES (?, ?, ?)",
            (source, problem_id, json.dumps(embedding)),
            commit=True,
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO problem_embeddings (
                source, problem_id, rewritten_content, model, dim, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, problem_id, rewritten_content, model, dim, updated_at),
            commit=True,
        )

    async def save_embedding(
        self,
        source: str,
        problem_id: str,
        rewritten_content: str,
        model: str,
        dim: int,
        embedding: List[float],
    ) -> None:
        await asyncio.to_thread(
            self._save_embedding_sync,
            source,
            problem_id,
            rewritten_content,
            model,
            dim,
            embedding,
        )

    def _delete_all_embeddings_sync(self, source: Optional[str] = None) -> None:
        if source:
            self.db.execute(
                "DELETE FROM problem_embeddings WHERE source = ?",
                (source,),
                commit=True,
            )
            self.db.execute(
                "DELETE FROM vec_embeddings WHERE source = ?",
                (source,),
                commit=True,
            )
            return
        self.db.execute("DELETE FROM problem_embeddings", commit=True)
        self.db.execute("DELETE FROM vec_embeddings", commit=True)

    async def delete_all_embeddings(self, source: Optional[str] = None) -> None:
        await asyncio.to_thread(self._delete_all_embeddings_sync, source)

    def _search_similar_sync(
        self,
        query_embedding: List[float],
        source: Optional[str],
        top_k: int,
        min_similarity: float,
    ) -> List[dict]:
        over_fetch_k = max(top_k * 4, top_k)
        rows = self.db.execute(
            """
            SELECT source, problem_id, distance
            FROM vec_embeddings
            WHERE embedding MATCH ?
              AND k = ?
            """,
            (json.dumps(query_embedding), over_fetch_k),
            fetchall=True,
        )
        results: List[dict] = []
        if not rows:
            return results
        for src, problem_id, distance in rows:
            if source and source != "all" and src != source:
                continue
            similarity = 1 - distance
            if similarity < min_similarity:
                continue
            results.append(
                {
                    "source": src,
                    "problem_id": problem_id,
                    "distance": distance,
                    "similarity": similarity,
                }
            )
        return results[:top_k]

    async def search_similar(
        self,
        query_embedding: List[float],
        source: Optional[str],
        top_k: int,
        min_similarity: float,
    ) -> List[dict]:
        return await asyncio.to_thread(
            self._search_similar_sync,
            query_embedding,
            source,
            top_k,
            min_similarity,
        )

    def _count_table_sync(
        self,
        table: str,
        source: Optional[str] = None,
        filter_pattern: Optional[str] = None,
    ) -> int:
        if table not in ("vec_embeddings", "problem_embeddings"):
            raise ValueError(f"Invalid table name: {table}")
        conditions = []
        params: list = []
        if source:
            conditions.append("source = ?")
            params.append(source)
        if filter_pattern:
            conditions.append("problem_id LIKE '%' || ? || '%'")
            params.append(filter_pattern)
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        row = self.db.execute(
            f"SELECT COUNT(*) FROM {table}{where_clause}",
            tuple(params) if params else (),
            fetchone=True,
        )
        return int(row[0]) if row else 0

    async def count_embeddings(self, source: Optional[str] = None, filter_pattern: Optional[str] = None) -> int:
        return await asyncio.to_thread(self._count_table_sync, "vec_embeddings", source, filter_pattern)

    async def count_metadata(self, source: Optional[str] = None, filter_pattern: Optional[str] = None) -> int:
        return await asyncio.to_thread(self._count_table_sync, "problem_embeddings", source, filter_pattern)
