import asyncio
import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .base import InspireOutput, LLMBase, TranslationOutput  # As a module
except ImportError:
    from llms.base import (  # When executed directly
        InspireOutput,
        LLMBase,
        TranslationOutput,
    )

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from utils.logger import get_llm_logger

logger = get_llm_logger()


class GeminiBaseModel(BaseModel):
    pass


class GeminiTranslationOutput(GeminiBaseModel):
    thinking: str = Field(description="Translation reasoning")
    translation: str = Field(description="Translated content")


class GeminiInspireOutput(GeminiBaseModel):
    thinking: str = Field(description="Problem analysis thinking")
    traps: str = Field(description="Common pitfalls")
    algorithms: str = Field(description="Recommended algorithms")
    inspiration: str = Field(description="Extra hints")


class GeminiLLM(LLMBase):
    """
    GeminiLLM is a wrapper for Google Gemini (Google Generative AI) using google-genai SDK.

    This class provides a simple interface for generating text using Gemini models.

    When initialized, it automatically reads the API key from the environment variable GOOGLE_GEMINI_API_KEY.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = 2,
        base_url: str = None,
    ):
        """
        Initialize the GeminiLLM instance.

        Args:
            api_key (str, optional): Google Gemini API Key
            model (str, optional): The name of the Gemini model to use, default is "gemini-2.0-flash"
            temperature (float, optional): The temperature parameter for the model, default is 0.7
            max_tokens (int, optional): The maximum number of tokens to generate, default is None
            timeout (int, optional): The timeout for the request in seconds, default is None
            max_retries (int, optional): The maximum number of retries for the request, default is 2
            base_url (str, optional): Base URL for third-party proxy, default is None
        """
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("請設定 GOOGLE_GEMINI_API_KEY 環境變數或傳入 api_key 參數")

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model_name = model

        # Build HTTP options with timeout and retry settings
        http_options = types.HttpOptions(
            base_url=base_url,
            timeout=timeout * 1000 if timeout else None,  # HttpOptions expects milliseconds
            retry_options=types.HttpRetryOptions(
                attempts=max_retries + 1,  # attempts includes the initial request
            ),
        )

        self.genai_client = genai.Client(
            api_key=self.api_key,
            http_options=http_options,
        )

    @staticmethod
    def _schema_to_json(schema: type) -> dict | None:
        if hasattr(schema, "model_json_schema"):
            return schema.model_json_schema()
        if hasattr(schema, "schema"):
            return schema.schema()
        return None

    @staticmethod
    def _parse_schema_response(schema: type, text: str) -> object | None:
        if hasattr(schema, "model_validate_json"):
            return schema.model_validate_json(text)
        if hasattr(schema, "parse_raw"):
            return schema.parse_raw(text)
        return None

    @staticmethod
    def _select_gemini_schema(schema: type) -> type | None:
        if schema in (TranslationOutput, GeminiTranslationOutput):
            return GeminiTranslationOutput
        if schema in (InspireOutput, GeminiInspireOutput):
            return GeminiInspireOutput
        if isinstance(schema, type) and issubclass(schema, GeminiBaseModel):
            return schema
        return None

    async def _invoke_structured_output(self, prompt: str, schema: type) -> object | None:
        gemini_schema = self._select_gemini_schema(schema)
        if not gemini_schema:
            return None
        json_schema = self._schema_to_json(gemini_schema)
        if not json_schema:
            return None
        try:
            config_kwargs = {
                "response_mime_type": "application/json",
                "response_json_schema": json_schema,
            }
            if self.temperature is not None:
                config_kwargs["temperature"] = self.temperature
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config_kwargs,
            )
        except Exception as exc:
            logger.warning("Structured output failed: %s", exc, exc_info=True)
            return None

        text = getattr(response, "text", None)
        if not text:
            return None
        parsed = self._parse_schema_response(gemini_schema, text)
        if parsed is None:
            logger.warning("Structured output JSON parse failed", exc_info=True)
        return parsed

    async def generate(self, prompt: str) -> str:
        """
        Generate a response from the LLM based on the input prompt.

        Args:
            prompt (str): The input prompt.

        Returns:
            str: The generated response.
        """
        config_kwargs = {}
        if self.temperature is not None:
            config_kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            config_kwargs["max_output_tokens"] = self.max_tokens

        response = await asyncio.to_thread(
            self.genai_client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=config_kwargs if config_kwargs else None,
        )
        return getattr(response, "text", "") or ""


if __name__ == "__main__":
    llm = GeminiLLM()

    res = llm.translate("今天天氣很好。", "en")
    print(res)
