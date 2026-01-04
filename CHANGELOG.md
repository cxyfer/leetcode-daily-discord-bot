# Changelog

All notable changes to this project will be documented in this file.

## [v1.1.1] - 2026-01-04
### Added
- **AI Rewritten Query Display**: `/similar` 指令現在會同時顯示原始查詢與 AI 重寫後的關鍵字，增加搜尋透明度。
- **Expanded Source Support**: 強化題目偵測邏輯，支援 LeetCode 比賽 (Contest)、Codeforces 與洛谷 (Luogu) 的網址及題目編號格式。
- **Multi-Platform URL Detection**: 支援包含 UVA、SPOJ 在內的洛谷轉錄題目格式，並優化 Codeforces 的 Contest/Problemset 網址解析。

### Improved
- **Dynamic Result Batching**: 搜尋結果現在採用字元長度感知的動態分頁機制，嚴格遵守 Discord 1024 字元欄位限制，避免發送失敗。
- **Increased Search Limit**: 將 `/similar` 的最大搜尋數量 `top_k` 從 10 提升至 20。
- **UI Polish**: 
  - 為搜尋結果區段加入 Emoji 標示 (❓, 🤖, 🔍)。
  - 優化結果清單的格式化，包括來源標籤 (Source tag) 的空格一致性。
  - 使用全域 UI 常數標準化顯示效果。

### Fixed
- 修復網址偵測缺失導致部分 LeetCode 連結無法被識別為題目 ID 的問題。
- 修復無效來源前綴 (Source Prefix) 的驗證邏輯，避免非預期的字串被解析為題目來源。
- 修正巢狀前綴 (Nested Prefix) 的遞迴處理邏輯。

## [v1.1.0] - 2026-01-01
### Added
- `/similar` command for semantic similarity search of LeetCode problems using embeddings.
- Embedding CLI tool (`embedding_cli.py`) for building and querying problem embeddings.
- `EmbeddingRewriter`, `EmbeddingGenerator`, `EmbeddingStorage`, and `SimilaritySearcher` modules.
- Support for `.env` fallback mode with `DummyConfig` compatibility.

### Fixed
- Add empty rewrite validation with fallback in similar search.
- Add table whitelist validation to prevent SQL injection in storage.
- Add dimension type/range validation in `create_vec_table`.
- Fix `check_dimension_consistency` to return False on OperationalError.
- Remove redundant template assignment and duplicate imports.
- Change bare except to `except Exception` for proper exception handling.
- Fix variable shadowing in `similar_cog.py`.
- Add `cog_unload` to close database connection on unload.
- Add context manager protocol to `EmbeddingDatabaseManager`.
- Add embedding batch size mismatch check.
- Consolidate double retry logic in rewriter.

## [v1.0.2] - 2026-01-01
### Fixed
- Normalize LLM outputs to avoid inconsistent formatting.

### Documentation
- Add Docker run examples for both config.toml and .env setups.

### Maintenance
- Refresh the dependency lockfile for consistency.

## [v1.0.1] - 2026-01-01
### Fixed
- Use langchain-core prompt templates for improved LLM compatibility.

## [v1.0.0] - 2026-01-01
### Added
- Docker image publishing and documentation via GHCR workflow.

## Pre-1.0.0
### Added
- Automatic daily challenge posting with scheduled delivery per server.
- Slash commands for daily challenges, problem lookup, recent submissions, and server setup.
- Multi-server configuration with per-server channels, roles, and timezones.
- LeetCode.cn daily challenge support.
- LLM-powered translation and inspiration with caching.
- Historical daily challenges and monthly challenge fetching.
- Interactive embeds for problem details, submissions, and overview navigation.

### Improved
- Structured logging and APScheduler-based scheduling reliability.
- Data storage and caching for problem information and ratings.

### Fixed
- Scheduling, timezone handling, and interaction edge cases.
- Fix inspiration embed field names to display Chinese titles. (commit 5ec4446)
