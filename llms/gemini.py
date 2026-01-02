import asyncio
import json
import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .base import LLMBase  # As a module
except ImportError:
    from llms.base import LLMBase  # When executed directly

from google import genai
from google.genai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.logger import get_llm_logger

logger = get_llm_logger()


class GeminiLLM(LLMBase):
    """
    GeminiLLM is a wrapper for Google Gemini (Google Generative AI) using langchain.

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
    ):
        """
        Initialize the GeminiLLM instance.

        Args:
            api_key (str, optional): Google Gemini API Key
            model (str, optional): The name of the Gemini model to use, default is "gemini-2.0-flash"
            temperature (float, optional): The temperature parameter for the model, default is 0.7
            max_tokens (int, optional): The maximum number of tokens to generate, default is None
            timeout (int, optional): The timeout for the request, default is None
            max_retries (int, optional): The maximum number of retries for the request, default is 2
        """
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("請設定 GOOGLE_GEMINI_API_KEY 環境變數或傳入 api_key 參數")

        self.temperature = temperature
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=self.api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.genai_client = genai.Client(api_key=self.api_key)
        self.model_name = model

    @staticmethod
    def _schema_to_json(schema: type) -> dict | None:
        if hasattr(schema, "model_json_schema"):
            return schema.model_json_schema()
        if hasattr(schema, "schema"):
            return schema.schema()
        return None

    async def _invoke_structured_output(self, prompt: str, schema: type) -> object | None:
        json_schema = self._schema_to_json(schema)
        if not json_schema:
            return None
        try:
            config_kwargs = {
                "response_mime_type": "application/json",
                "response_json_schema": json_schema,
            }
            if self.temperature is not None:
                config_kwargs["temperature"] = self.temperature
            config = types.GenerateContentConfig(**config_kwargs)
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            logger.warning("Structured output failed: %s", exc, exc_info=True)
            return None

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            return parsed
        text = getattr(response, "text", None)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Structured output JSON parse failed", exc_info=True)
            return None

    async def generate(self, prompt: str) -> str:
        """
        Generate a response from the LLM based on the input prompt.

        Args:
            prompt (str): The input prompt.

        Returns:
            str: The generated response.
        """
        result = await self.llm.ainvoke(prompt)
        if hasattr(result, "content"):
            return result.content
        return str(result)


if __name__ == "__main__":
    llm = GeminiLLM()

    res = llm.translate("今天天氣很好。", "en")
    print(res)
