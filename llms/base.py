from abc import ABC, abstractmethod
import json
from langchain_core.output_parsers import SimpleJsonOutputParser

from llms.templates import (
    TRANSLATION_JSON_PROMPT_TEMPLATE,
    INSPIRE_JSON_PROMPT_TEMPLATE,
)
from utils.logger import get_llm_logger

logger = get_llm_logger()

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
        response = await self.generate(prompt)
        response_text = self._normalize_response(response)
        parser = SimpleJsonOutputParser()
        try:
            parsed = parser.parse(response_text)
            return parsed
        except Exception:
            return {"raw": response_text}
