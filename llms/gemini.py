
import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .base import LLMBase  # As a module
except ImportError:
    from llms.base import LLMBase  # When executed directly

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import SimpleJsonOutputParser

class GeminiLLM(LLMBase):
    """
    GeminiLLM is a wrapper for Google Gemini (Google Generative AI) using langchain.

    This class provides a simple interface for generating text using Gemini models.

    When initialized, it automatically reads the API key from the environment variable GOOGLE_GEMINI_API_KEY.
    """

    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash",
                 temperature: float = 0.7, max_tokens: int = None,
                 timeout: int = None, max_retries: int = 2):
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
        
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=self.api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.model_name = model

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
 
