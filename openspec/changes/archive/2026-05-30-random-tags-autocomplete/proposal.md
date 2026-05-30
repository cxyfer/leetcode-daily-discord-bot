## Why

目前 `/random` 指令的 `tags` 參數是自由文字輸入，使用者需要憑記憶或猜測來輸入標籤名稱（如 "Array"、"Dynamic Programming"），容易打錯字或根本不知道有哪些可用標籤。而 upstream API 已提供 `GET /api/v1/tags/{source}` 端點可查詢每個來源的有效標籤清單。利用此端點為 `tags` 參數加上 autocomplete，能大幅提升使用者體驗並減少輸入錯誤。

## What Changes

- 在 `OjApiClient` 新增 `get_tags(source)` 方法，呼叫 `GET /api/v1/tags/{source}` 取得標籤清單
- 在 `OjApiClient` 新增 TTL 快取層 (`get_tags_cached`)，避免重複請求 API，並在 API 失敗時 graceful degradation
- 為 `/random` 指令的 `tags` 參數加上 `@autocomplete` callback，根據使用者當前選擇的 `source` 動態提供標籤建議
- 啟動時可選地預載 `leetcode` 和 `codeforces` 的標籤，讓首次使用 autocomplete 時無延遲
- 新增對應的測試覆蓋

## Capabilities

### New Capabilities

- `tag-autocomplete`: 為 `/random` 指令的 `tags` 參數提供動態 autocomplete，根據選擇的題目來源（LeetCode、Codeforces 等）從 API 取得有效標籤清單，附帶 TTL 快取與錯誤容錯

### Modified Capabilities

- `slash-commands`: 新增 tags autocomplete 相關的 scenario（autocomplete 根據 source 動態載入、API 失敗時 fallback 為空清單、無 source 時預設 leetcode）

## Impact

- `src/bot/api_client.py` — 新增 `get_tags()` 和 `get_tags_cached()` 方法，以及 `_tags_cache` 內部狀態
- `src/bot/cogs/slash_commands_cog.py` — 新增 `@random_command.autocomplete("tags")` callback
- `src/bot/app.py` — 可選的啟動預載入邏輯（`on_ready` 中 fire-and-forget）
- `tests/test_random_command.py` — 新增 autocomplete 與 `get_tags` 方法的測試
