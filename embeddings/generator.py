"""Gemini embedding generator for similarity search."""

from __future__ import annotations

import asyncio
import os
from typing import List, Sequence

from google import genai
from google.genai import errors, types
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from utils.config import ConfigManager, EmbeddingModelConfig, get_config
from utils.logger import get_llm_logger

logger = get_llm_logger()


def _resolve_api_key(config: ConfigManager) -> str | None:
    return (
        config.gemini_api_key
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_GEMINI_API_KEY")
    )


def _is_retryable_api_error(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code in {429, 503}
    return False


class EmbeddingGenerator:
    def __init__(self, config: ConfigManager | None = None):
        self.config = config or get_config()
        self.model_config: EmbeddingModelConfig = self.config.get_embedding_model_config()
        api_key = _resolve_api_key(self.config)
        if not api_key:
            raise ValueError("Gemini API key not configured")
        self.client = genai.Client(api_key=api_key)
        self._embed_config = self._build_embed_config()

    def _build_embed_config(self):
        try:
            return types.EmbedContentConfig(
                task_type=self.model_config.task_type,
                output_dimensionality=self.model_config.dim,
            )
        except Exception:  # pragma: no cover - fallback for SDK differences
            return {
                "task_type": self.model_config.task_type,
                "output_dimensionality": self.model_config.dim,
            }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception(_is_retryable_api_error),
        reraise=True,
    )
    def _embed_sync(self, contents: Sequence[str]):
        return self.client.models.embed_content(
            model=self.model_config.name,
            contents=list(contents),
            config=self._embed_config,
        )

    @staticmethod
    def _extract_vectors(result) -> List[List[float]]:
        raw_embeddings = getattr(result, "embeddings", None)
        if raw_embeddings is None and isinstance(result, dict):
            raw_embeddings = result.get("embeddings")
        if raw_embeddings is None:
            return []
        vectors: List[List[float]] = []
        for embedding in raw_embeddings:
            if hasattr(embedding, "values"):
                values = embedding.values
            elif isinstance(embedding, dict) and "values" in embedding:
                values = embedding["values"]
            elif hasattr(embedding, "embedding"):
                values = embedding.embedding
            else:
                values = embedding
            vectors.append(list(values))
        return vectors

    async def embed(self, content: str) -> List[float]:
        vectors = await self.embed_batch([content])
        return vectors[0] if vectors else []

    async def embed_batch(self, contents: Sequence[str]) -> List[List[float]]:
        if not contents:
            return []
        result = await asyncio.to_thread(self._embed_sync, contents)
        vectors = self._extract_vectors(result)
        if len(vectors) != len(contents):
            logger.warning(
                "Embedding count mismatch: expected %s got %s",
                len(contents),
                len(vectors),
            )
        return vectors
