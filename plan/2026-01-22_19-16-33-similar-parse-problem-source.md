---
mode: plan
cwd: /mnt/d/Workspace/Github/leetcode-daily-discord-bot
task: /similar 新增題目來源參數並沿用 /problem 解析與既有向量
complexity: medium
planning_method: builtin
created_at: 2026-01-22T19:16:36+08:00
---

# Plan: /similar 題目來源解析與向量重用

🎯 任務概述
在 /similar 指令新增一個可輸入題目來源/題號的參數，解析方式與 /problem 一致，
若該題已在向量索引中，直接使用既有向量進行相似搜尋，避免重新向量化。

📋 執行計畫
1. 釐清指令介面：新增 /similar 參數（例如 problem），定義與 query 的互斥或優先規則，並確認 source 仍作為結果來源過濾。
2. 擴充 EmbeddingStorage：新增讀取既有向量的方法（依 source + problem_id），必要時同時取出 rewritten_content 以供顯示。
3. 調整 /similar 流程：當 problem 參數存在時用 detect_source 解析來源與題號，查詢既有向量並直接 search；若不存在則回傳清楚訊息或回退到 query 流程。
4. 更新輸出呈現：在 embed 中顯示 problem 輸入與（若有）既有 rewritten_content，避免顯示空白 AI 重寫欄位。
5. 測試與文件：新增 /similar 新分支的單元測試（mock storage/rewriter/generator），並更新 README 使用說明。

⚠️ 風險與注意事項
- 若 source 參數同時被用作結果過濾與 problem 解析，需定義清楚優先順序以避免語義混淆。
- vec_embeddings 的向量格式需確認可安全讀回為 list[float]，否則可能導致 search 失敗。

📎 參考
- `cogs/similar_cog.py:51`
- `cogs/slash_commands_cog.py:168`
- `utils/source_detector.py:29`
- `embeddings/storage.py:16`
- `utils/database.py:640`
