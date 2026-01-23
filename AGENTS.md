# Repository Guidelines

## 專案結構與模組
- `bot.py`: 主要入口與 Discord bot 啟動流程。
- `cogs/`: Discord 指令與互動處理（slash commands、排程、相似題等）。
- `leetcode.py` / `embedding_cli.py`: 維運用 CLI 工具（補資料、建立 embedding）。
- `embeddings/`、`llms/`、`utils/`: 向量索引、LLM 介面、設定/資料庫/日誌共用模組。
- `tests/`: pytest 測試與測試說明；`tests/README.md` 有更完整的測試指引。
- `config.toml.example` / `.env.example`: 設定範本；`data/migrate_settings.sql` 為升級遷移腳本。
- `data/`、`logs/`：執行期資料與記錄（本地或容器掛載）。

## 建置、測試與開發指令
- 執行 bot：`uv run bot.py`
- 執行所有測試：`uv run python -m pytest tests/ -v`
- 單檔測試：`uv run python -m pytest tests/test_monthly_fetch.py -v`
- 覆蓋率：`uv run python -m pytest tests/ -v --cov=leetcode --cov-report=term-missing`
- 建立相似題索引：`uv run python embedding_cli.py --build`
- 檢視/查詢向量索引：`uv run python embedding_cli.py --stats`、`uv run python embedding_cli.py --query "two sum"`
- 補齊題目內容：`uv run python leetcode.py --missing-content-stats`、`uv run python leetcode.py --fill-missing-content`

## 程式碼風格與命名
- Python 4 空白縮排，維持與現有檔案一致。
- 命名慣例：module/函式/變數使用 `snake_case`，類別使用 `CamelCase`，常數用 `UPPER_SNAKE_CASE`。
- 專案未見強制 formatter 設定；若使用格式化工具（例如 ruff format），請僅整理修改檔並避免大規模純格式變更。
- 檔名以小寫英文為主，避免空白；新增檔案請放到現有模組內以利維護。
- 註解以繁體中文為主，保持精簡與可讀。

## 測試規範
- 使用 pytest + pytest-asyncio + pytest-cov。
- 非同步測試需標記 `@pytest.mark.asyncio`。
- 測試檔名採 `tests/test_*.py`；測試類別用 `Test*` 命名。
- 外部服務（Discord API、LLM、資料庫）請以 mock/fixture 隔離。

## Commit 與 Pull Request
- commit 格式偏向「emoji + conventional type + optional scope」，例如：`🐛fix(logger): defer config load`、`✨feat(similar): add /similar command`。
- PR 請包含：變更摘要、動機/影響範圍、測試結果（貼出執行指令），必要時附上行為變更說明或螢幕截圖。
- 若涉及資料庫或設定變動，請提供遷移說明與回滾策略。

## CI 與版本發佈
- `.github/workflows/ghcr.yml` 於 tag `v*.*.*` 時建置並推送 GHCR 映像。
- 發佈前請確認 `CHANGELOG.md` 與版本號一致，避免重寫已釋出的 tag。

## 設定與安全
- 優先使用 `config.toml`，`.env` 僅為相容性；不要提交任何 token。
- `data/data.db` 與 `logs/` 請保留在本機或掛載到容器磁碟以避免資料遺失。
- 設定鍵新增或調整時，請同步更新 `config.toml.example` 與 `README.md`。
