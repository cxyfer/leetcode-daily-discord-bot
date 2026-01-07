"""Problem statement rewriter using Gemini models."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import Executor
from typing import Optional

from google import genai
from google.genai import errors, types
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from utils.config import ConfigManager, RewriteModelConfig, get_config
from utils.logger import get_llm_logger

logger = get_llm_logger()

REWRITE_PROMPT = """Role: Competitive Programming Problem Simplifier

Task: Rewrite the given problem statement into its core algorithmic essence. The output must be concise,
self-contained, and immediately understandable without referencing the original.

Instructions:

1.  **Content to REMOVE**:
    *   All storytelling, legends, character names, and background context.
    *   All examples and their explanations.
    *   Redundant phrasing.

2.  **Content to KEEP**:
    *   The core problem definition and objective.

3.  **HTML Processing**:
    *   Extract text content from semantic tags like `<span data-keyword="...">`
        (e.g., `<span data-keyword="binary-array">binary array</span>` → "binary array").
    *   Convert mathematical HTML to MathJax:
        *   `<sup>` → `^{{}}` (e.g., `10<sup>9</sup>` → $10^9$)
        *   `<sub>` → `_{{}}` (e.g., `a<sub>i</sub>` → $a_i$)
        *   `<code>` variables → inline math (e.g., `<code>n</code>` → $n$)

4.  **Language**: If the original is not in English, translate to English.

5.  **Output Format**:
    *   Use MathJax ($...$) for all math.
    *   Be as succinct as possible while remaining unambiguous.
    *   **Output ONLY the simplified statement. No preamble, no labels, no markdown fences.**

Input Statement:
{ORIGINAL}
"""


def _resolve_api_key(config: ConfigManager) -> Optional[str]:
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


class EmbeddingRewriter:
    def __init__(self, config: ConfigManager | None = None):
        self.config = config or get_config()
        self.model_config: RewriteModelConfig = self.config.get_rewrite_model_config()

        # Resolve API key: model-specific -> global -> env
        api_key = self.model_config.api_key or _resolve_api_key(self.config)
        if not api_key:
            raise ValueError("Gemini API key not configured")

        # Resolve base_url with inheritance logic
        model_base_url = self.model_config.base_url
        global_base_url = self.config.gemini_base_url

        if model_base_url and not self.model_config.api_key:
            # base_url set without api_key -> error
            raise ValueError(
                "Rewrite model has base_url configured but no api_key. "
                "Please also set api_key in [llm.gemini.models.rewrite]"
            )

        # Use model-specific base_url if set, otherwise inherit global
        base_url = model_base_url or global_base_url

        # Debug logging for configuration
        logger.debug(
            "EmbeddingRewriter config: model=%s, api_key=%s, base_url=%s (model=%s, global=%s)",
            self.model_config.name,
            f"{api_key[:8]}..." if api_key else None,
            base_url,
            model_base_url,
            global_base_url,
        )

        http_options = types.HttpOptions(base_url=base_url) if base_url else None
        self.client = genai.Client(api_key=api_key, http_options=http_options)

    def _build_prompt(self, original: str) -> str:
        return REWRITE_PROMPT.format(ORIGINAL=original)

    def _build_generation_config(self):
        try:
            return types.GenerateContentConfig(temperature=self.model_config.temperature)
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
            retry=retry_if_exception(_is_retryable_api_error),
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

    async def rewrite_with_executor(self, content: str, executor: Optional[Executor]) -> str:
        if not content or not content.strip():
            return ""
        prompt = self._build_prompt(content)
        try:
            return await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(executor, self._rewrite_sync, prompt),
                timeout=self.model_config.timeout,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Rewrite timed out after %s seconds",
                self.model_config.timeout,
            )
            raise
