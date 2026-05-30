## Why

`/similar` 相似題目查詢目前使用與一般 API 相同的 10 秒 timeout，但後端 embedding 計算可能需要數十秒甚至上百秒。同時，後端 API 對不同失敗情境回傳不同的 HTTP 狀態碼（400/404/502/504），目前全部被歸類為「查詢失敗」，用戶無法得知真正原因。

本 change 解決兩個核心問題：
1. **Timeout 不夠長**：10 秒對 embedding 查詢遠不足夠，需拉到 300 秒以上且可設定
2. **錯誤訊息太粗糙**：502（embedding 服務掛了）、504（embedding 逾時）、400（查詢格式無效）全部顯示一樣的「查詢失敗」

## What Changes

- `config.toml` 的 `[similar]` section 新增 `timeout` 欄位，預設值 **300 秒**
- `SimilarConfig` dataclass 新增 `timeout` 欄位
- `OjApiClient` 的 `search_similar_by_id()` 和 `search_similar_by_text()` 接受 per-request timeout 參數，覆蓋 session 層級的短 timeout
- `OjApiClient` 新增 `ApiEmbeddingError(502)` 和 `ApiEmbeddingTimeoutError(504)` 例外類別
- `/similar` slash command 和按鈕觸發的 similar 查詢都使用 config 中的長 timeout
- 依據 HTTP 狀態碼給予不同的 i18n 錯誤訊息（zh-TW/en-US/zh-CN）

## Capabilities

### New Capabilities
- `similar-error-handling`: `/similar` 和按鈕觸發的相似題目查詢能依據後端 HTTP 狀態碼（400/404/502/504）輸出對應的本地化錯誤訊息，且能區分 client 端 timeout 與 server 端 embedding timeout

### Modified Capabilities
- `configuration`: `SimilarConfig` dataclass 新增 `timeout` 欄位，`get_similar_config()` 需讀取並回傳該欄位
- `embedding-search`: similar API 呼叫改為使用 per-request timeout 覆蓋機制，且錯誤處理需區分 `ApiError`、`ApiEmbeddingError`、`ApiEmbeddingTimeoutError` 等不同例外

## Impact

- `src/bot/api_client.py` — 新增例外類別、`_request` 接受 timeout 參數、similar 方法傳遞 timeout
- `src/bot/utils/config.py` — `SimilarConfig.timeout` 新增欄位
- `src/bot/cogs/similar_cog.py` — 使用新 timeout、區分錯誤碼
- `src/bot/cogs/interaction_handler_cog.py` — `_action_similar` 同上
- `src/bot/i18n/locales/{zh-TW,en-US,zh-CN}.json` — 新增錯誤訊息 keys
- `config.toml` — `[similar]` 新增 `timeout` 欄位
- 無 breaking change，所有現有功能保持不變
