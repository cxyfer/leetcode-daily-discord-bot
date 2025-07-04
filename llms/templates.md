# llms/templates.py 模板重構規劃（修正版）

## 目標
- 將原本的 TRANSLATION_TEMPLATE 拆分為 System prompt（規則/角色）與 Human prompt（user 輸入）。
- templates.py 只保留 langchain 物件，移除原本的字串模板。

## 新結構範例

```python
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)

TRANSLATION_SYSTEM_PROMPT = SystemMessagePromptTemplate.from_template(
    "你是專業翻譯，請將下列內容翻譯成 {target_language}，請只輸出翻譯後的內容，不要有多餘說明。"
)
TRANSLATION_HUMAN_PROMPT = HumanMessagePromptTemplate.from_template("{content}")

TRANSLATION_CHAT_PROMPT = ChatPromptTemplate.from_messages([
    TRANSLATION_SYSTEM_PROMPT,
    TRANSLATION_HUMAN_PROMPT,
])
```

## 使用範例

```python
from llms.templates import TRANSLATION_CHAT_PROMPT

prompt = TRANSLATION_CHAT_PROMPT.format_messages(
    target_language="英文",
    content="今天天氣很好。"
)
# prompt 會是一組 Message 物件，可直接傳給 langchain LLM
```

## Mermaid 流程圖

```mermaid
flowchart TD
    A[System prompt: 翻譯規則/角色] --> C[ChatPromptTemplate]
    B[Human prompt: {content}] --> C
    C --> D[format_messages 輸出 Message 組]
    D --> E[傳給 LLM]
```

## 實作步驟

1. 修改 llms/templates.py：
    - 移除原本的 TRANSLATION_TEMPLATE 字串。
    - import langchain.prompts 的 SystemMessagePromptTemplate、HumanMessagePromptTemplate、ChatPromptTemplate。
    - 定義 TRANSLATION_SYSTEM_PROMPT、TRANSLATION_HUMAN_PROMPT、TRANSLATION_CHAT_PROMPT。

2. 其他程式如需使用翻譯模板，直接 import TRANSLATION_CHAT_PROMPT。

3. 不需修改 GeminiLLM，維持現有 generate(prompt: str) 介面。

## 注意事項

- 若未來有多個 prompt，可依此模式擴充。
- 若 langchain 版本不同，請確認 import 路徑（如 langchain_core.prompts）。