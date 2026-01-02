from abc import ABC, abstractmethod
import json
from langchain_core.output_parsers import SimpleJsonOutputParser
from pydantic import BaseModel

from llms.templates import (
    TRANSLATION_JSON_PROMPT_TEMPLATE,
    INSPIRE_JSON_PROMPT_TEMPLATE,
)
from utils.logger import get_llm_logger

logger = get_llm_logger()


class TranslationOutput(BaseModel):
    thinking: str
    translation: str


class InspireOutput(BaseModel):
    thinking: str
    traps: str
    algorithms: str
    inspiration: str


class LLMBase(ABC):
    """
    LLMBase is the abstract base class for all LLM implementations.
    All subclasses must implement the generate method.

    Methods:
        generate(prompt: str) -> str
            Generate a response from the LLM based on the input prompt.
    """

    def __init__(self):
        self.llm = None
        self.model_name = None

    @staticmethod
    def _normalize_response(response) -> str:
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        if isinstance(response, list):
            parts = []
            for item in response:
                if isinstance(item, dict):
                    text = item.get("text")
                    parts.append(str(text) if text is not None else str(item))
                else:
                    parts.append(str(item))
            return "".join(parts)
        if isinstance(response, dict):
            if "text" in response:
                return str(response["text"])
            return json.dumps(response, ensure_ascii=False)
        return str(response)

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        Generate a response from the LLM based on the input prompt.

        Args:
            prompt (str): The input prompt.

        Returns:
            str: The generated response.
        """
        pass

    async def _invoke_structured_output(self, prompt: str, schema: type) -> object | None:
        if not self.llm or not hasattr(self.llm, "with_structured_output"):
            return None
        try:
            structured_llm = self.llm.with_structured_output(schema)
            return await structured_llm.ainvoke(prompt)
        except Exception as exc:
            logger.warning(
                "Structured output failed: %s", exc, exc_info=True
            )
            return None

    async def translate(
        self, content: str, target_language: str, from_lang: str = "auto"
    ) -> str:
        """
        Translate the input content to the target language using the LLM.

        Args:
            content (str): The text to be translated.
            from_lang (str): The source language for translation., default is "auto"
            target_language (str): The target language for translation, default is "zh-TW"

        Returns:
            str: The translated text, or the original LLM response if parsing fails.
        """

        logger.debug(f"Translation text: {content}")
        prompt = TRANSLATION_JSON_PROMPT_TEMPLATE.format(
            to=target_language,
            from_lang=from_lang,
            text=content,
        )

        structured = await self._invoke_structured_output(prompt, TranslationOutput)
        if structured is not None:
            if isinstance(structured, dict):
                translation = structured.get("translation")
                if translation is not None:
                    return translation
            translation = getattr(structured, "translation", None)
            if translation is not None:
                return translation

        response = await self.generate(prompt)
        response_text = self._normalize_response(response)
        logger.debug(f"Translation response: {response_text}")
        parser = SimpleJsonOutputParser()
        try:
            parsed = parser.parse(response_text)
            return parsed.get("translation", response_text)
        except Exception:
            return response_text

    async def inspire(self, content: str, tags: list, difficulty: str) -> dict:
        """
        根據題目描述、tags、難度，產生解題靈感（僅繁體中文，禁止程式碼），回傳 JSON dict。
        Args:
            content (str): 題目描述
            tags (list): 題目標籤
            difficulty (str): 題目難度
        Returns:
            dict: { "thinking": ..., "traps": ..., "algorithms": ..., "inspiration": ... }
                  若解析失敗則回傳 {"raw": response}
        """
        prompt = INSPIRE_JSON_PROMPT_TEMPLATE.format(
            text=content, tags=", ".join(tags) if tags else "", difficulty=difficulty
        )
        structured = await self._invoke_structured_output(prompt, InspireOutput)
        if structured is not None:
            if isinstance(structured, dict):
                return structured
            fields = ("thinking", "traps", "algorithms", "inspiration")
            if all(hasattr(structured, field) for field in fields):
                return {field: getattr(structured, field) for field in fields}

        response = await self.generate(prompt)
        response_text = self._normalize_response(response)
        parser = SimpleJsonOutputParser()
        try:
            parsed = parser.parse(response_text)
            return parsed
        except Exception:
            return {"raw": response_text}
