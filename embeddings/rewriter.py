"""Problem statement rewriter using Gemini models."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import Executor
from typing import Optional

from google import genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from google.genai import types
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.config import ConfigManager, RewriteModelConfig, get_config
from utils.logger import get_llm_logger

logger = get_llm_logger()

REWRITE_PROMPT = """I have the following competitive programming problem that I want to show someone else:

=======
[[ORIGINAL]]
=======

Strip off all the stories, legends, characters, backgrounds, examples, well-known definitions etc. from the statement while still enabling everyone to understand the problem. Also remove the name of the character if applicable. If it is not in English translate it. Make it as succinct as possible while still being understandable. Try to avoid formulas and symbols. Abstract freely - for example, if the problem is about buying sushi, you can just phrase it as a knapsack problem. If necessary, mathjax ($...$) for math. Provide the *succinct* simplified statement directly without jargon. Start your response with "Simplified statement:".
"""


def _resolve_api_key(config: ConfigManager) -> Optional[str]:
    return (
        config.gemini_api_key
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_GEMINI_API_KEY")
    )


class EmbeddingRewriter:
    def __init__(self, config: ConfigManager | None = None):
        self.config = config or get_config()
        self.model_config: RewriteModelConfig = self.config.get_rewrite_model_config()
        api_key = _resolve_api_key(self.config)
        if not api_key:
            raise ValueError("Gemini API key not configured")
        self.client = genai.Client(api_key=api_key)

    def _build_prompt(self, original: str) -> str:
        return REWRITE_PROMPT.replace("[[ORIGINAL]]", original)

    def _build_generation_config(self):
        try:
            return types.GenerateContentConfig(
                temperature=self.model_config.temperature
            )
        except Exception:  # pragma: no cover - fallback for SDK differences
            return {"temperature": self.model_config.temperature}

    def _extract_text(self, response) -> str:
        if hasattr(response, "text"):
            return response.text or ""
        if isinstance(response, dict) and "text" in response:
            return response.get("text", "") or ""
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            content = getattr(candidate, "content", None)
            if isinstance(content, str):
                return content
        return str(response) if response is not None else ""

    def _rewrite_sync(self, prompt: str) -> str:
        retryer = Retrying(
            stop=stop_after_attempt(self.model_config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
            reraise=True,
        )
        for attempt in retryer:
            with attempt:
                try:
                    response = self.client.models.generate_content(
                        model=self.model_config.name,
                        contents=prompt,
                        config=self._build_generation_config(),
                        timeout=self.model_config.timeout,
                    )
                except TypeError:
                    response = self.client.models.generate_content(
                        model=self.model_config.name,
                        contents=prompt,
                        config=self._build_generation_config(),
                    )
                return self._extract_text(response)
        return ""

    async def rewrite(self, content: str) -> str:
        return await self.rewrite_with_executor(content, None)

    async def rewrite_with_executor(
        self, content: str, executor: Optional[Executor]
    ) -> str:
        if not content or not content.strip():
            return ""
        prompt = self._build_prompt(content)
        max_attempts = max(1, self.model_config.max_retries)
        for attempt in range(1, max_attempts + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        executor, self._rewrite_sync, prompt
                    ),
                    timeout=self.model_config.timeout,
                )
            except asyncio.TimeoutError:
                if attempt < max_attempts:
                    wait_seconds = min(2**attempt, 30)
                    logger.warning(
                        "Rewrite timed out after %s seconds (attempt %s/%s), retrying in %ss",
                        self.model_config.timeout,
                        attempt,
                        max_attempts,
                        wait_seconds,
                    )
                    await asyncio.sleep(wait_seconds)
                    continue
                logger.error(
                    "Rewrite timed out after %s seconds (attempt %s/%s), giving up",
                    self.model_config.timeout,
                    attempt,
                    max_attempts,
                )
                raise
