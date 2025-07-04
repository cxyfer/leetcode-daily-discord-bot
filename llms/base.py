from abc import ABC, abstractmethod
from langchain_core.output_parsers import SimpleJsonOutputParser

from llms.templates import *

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

    async def translate(self, content: str, target_language: str, from_lang: str = "auto") -> str:
        """
        Translate the input content to the target language using the LLM.

        Args:
            content (str): The text to be translated.
            from_lang (str): The source language for translation., default is "auto"
            target_language (str): The target language for translation, default is "zh-TW"

        Returns:
            str: The translated text, or the original LLM response if parsing fails.
        """

        prompt = TRANSLATION_JSON_PROMPT_TEMPLATE.format(
            to=target_language,
            from_lang=from_lang,
            text=content,
        )

        response = await self.generate(prompt)
        parser = SimpleJsonOutputParser()
        try:
            parsed = parser.parse(response)
            return parsed["translation"]
        except Exception:
            return response

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
            text=content,
            tags=", ".join(tags) if tags else "",
            difficulty=difficulty
        )
        response = await self.generate(prompt)
        parser = SimpleJsonOutputParser()
        try:
            parsed = parser.parse(response)
            return parsed
        except Exception:
            return {"raw": response}

