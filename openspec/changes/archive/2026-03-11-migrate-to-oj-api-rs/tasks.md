# Tasks: Migrate problem data layer to oj-api-rs

## Phase 1: Foundation

### T1: Create api_client.py
- [x] 新增 `api_client.py`
- [x] Class `OjApiClient(base_url: str, token: str | None = None, timeout: int = 10)`
- [x] `__init__`: 儲存 config，不建立 session（延遲到 `start()`）
- [x] `async start()`: 建立 `aiohttp.ClientSession`
  - Connector: `aiohttp.TCPConnector(limit=50, limit_per_host=10, keepalive_timeout=30)`
  - 設定 `Authorization: Bearer {token}` header（若有 token）
  - 設定 `aiohttp.ClientTimeout(total=timeout)`
- [x] `async close()`: 關閉 session
- [x] Singleflight 實作：
  - `_inflight: dict[str, asyncio.Future]`
  - key 格式：`f"{method}:{path}?{sorted_params}"`
  - 有 inflight → `await _inflight[key]` 共用結果
  - 無 inflight → 建立 Future，執行 `_do_request()`，完成後從 dict 移除
- [x] `async _do_request(method, path, **kwargs) -> dict | None`: 實際 HTTP 請求
  - HTTP 200 → 回傳 JSON dict
  - HTTP 404 → 回傳 `None`
  - HTTP 202 → raise `ApiProcessingError(detail)`
  - HTTP 429 → 讀取 `Retry-After` header（預設 5s），`await asyncio.sleep(retry_after)`，重試一次；第二次 429 → raise `ApiRateLimitError(retry_after)`
  - 其他 4xx/5xx → raise `ApiError(status, detail)`（解析 RFC 7807 body）
  - `asyncio.TimeoutError` / `aiohttp.ClientError` → raise `ApiNetworkError(str(e))`
  - JSON decode 失敗 → raise `ApiError(status, "Invalid response body")`
- [x] `async _request(method, path, **kwargs) -> dict | None`: Singleflight wrapper over `_do_request`
- [x] `async get_problem(source: str, id: str) -> dict | None`
  - `GET /problems/{source}/{id}`
- [x] `async get_daily(domain: str = "com", date: str | None = None) -> dict | None`
  - `GET /daily` with query params `domain`, `date`
- [x] `async resolve(query: str) -> dict | None`
  - `GET /resolve/{query}`
  - 回傳 `{"source", "id", "problem"}` 或 None
- [x] `async search_similar_by_id(source: str, id: str, top_k: int = 5, min_similarity: float = 0.7) -> dict | None`
  - `GET /similar/{source}/{id}` with query params `limit=top_k`, `threshold=min_similarity`
- [x] `async search_similar_by_text(query: str, source: str | None = None, top_k: int = 5, min_similarity: float = 0.7) -> dict | None`
  - `GET /similar` with query params `q=query`, `source`, `limit=top_k`, `threshold=min_similarity`
- [x] Exception classes: `ApiError(status, detail)`, `ApiProcessingError(detail)`, `ApiNetworkError(detail)`, `ApiRateLimitError(retry_after)`

### T2: Update config for API settings
- [x] `utils/config.py`: 新增讀取 `[api]` section 的方法
  - `api_base_url` → 預設 `"https://oj-api.gdst.dev/api/v1"`
  - `api_token` → 預設 `None`
  - `api_timeout` → 預設 `10`
  - 環境變數 override: `API_BASE_URL`, `API_TOKEN`
- [x] `config.toml.example`: 新增 `[api]` section

## Phase 2: Core Migration

### T3: Initialize API client in bot.py
- [x] `bot.py`: import `OjApiClient`
- [x] 在 bot setup 中建立 `bot.api = OjApiClient(base_url, token, timeout)` 從 config 讀取
- [x] 在 `on_ready` 或 `setup_hook` 中呼叫 `bot.api.start()`
- [x] 在 `close()` 中呼叫 `bot.api.close()`
- [x] 移除 `bot.lcus.init_all_problems()` 呼叫
- [x] 移除 `bot.problems_db` 的建立（ProblemsDatabaseManager）
- [x] 移除 `bot.daily_db` 的建立（DailyChallengeDatabaseManager）
- [x] 移除 `bot.embedding_db` 的建立（EmbeddingDatabaseManager）
- [x] 保留 `bot.lcus`（精簡後，僅用於 /recent）
- [x] 移除 `bot.lccn` 的建立（CN daily 改由 API 提供）
- [x] 保留 `bot.db`（SettingsDatabaseManager）
- [x] 保留 `bot.llm_translate_db`, `bot.llm_inspire_db`

### T4: Unify button custom_id format in ui_helpers.py
- [x] `utils/ui_helpers.py` `create_problem_view()`:
  - 移除 source == "leetcode" 的特殊分支
  - 所有按鈕統一為 `problem|{source}|{id}|{action}`
  - action 值：`desc`, `translate`, `inspire`, `similar`
  - 範例：`problem|leetcode|1|desc`, `problem|codeforces|1A|similar`
- [x] `create_problems_overview_view()`:
  - Detail 按鈕格式統一為 `problem|{source}|{id}|desc`
  - 移除舊 `problem_detail|{source}|{id}|{domain}` 和 `problem_detail_{id}_{domain}` 格式
- [x] `create_submission_view()`:
  - 描述/翻譯/靈感按鈕統一為 `problem|{source}|{id}|{action}` 格式
- [x] `send_daily_challenge()`:
  - 確認接收 API response dict 格式（非舊 DB dict）
  - 確認 role mention、channel_id 模式正常運作
- [x] 移除 bot 上的 `LEETCODE_*_BUTTON_PREFIX` 常數引用
- [x] `create_daily_embed()` 和 `create_problem_embed()`: 確認接收 API 回應 dict 相容
  - `title_cn` 空字串 → 視為無中文標題
  - `difficulty` null → 顯示 "Unknown"
  - `rating` 0.0 → 不顯示 rating

### T5: Rewrite interaction_handler_cog.py button parsing
- [x] 移除所有 `leetcode_problem_*`, `leetcode_translate_*`, `leetcode_inspire_*`, `leetcode_similar_*` handler
- [x] 移除所有 `ext_problem|*`, `ext_translate|*`, `ext_inspire|*`, `ext_similar|*` handler
- [x] 新增統一 `on_interaction` listener，解析 `problem|{source}|{id}|{action}`:
  - 不符合 `problem|*` 模式的 custom_id → 靜默忽略（debug log）
  - **所有 action 在處理前先 `defer(ephemeral=True)`**，置於 `try/except discord.HTTPException` 內
  - `action == "desc"`: 呼叫 `bot.api.get_problem(source, id)` → `html_to_text(content)` → 回傳 embed
  - `action == "translate"`: 查 LLM 快取（`bot.llm_translate_db.get_translation(source, id)`） → miss 時呼叫 API 取 content → `html_to_text()` → LLM translate → 儲存快取（`source`, `id`）
  - `action == "inspire"`: 查 LLM 快取（`bot.llm_inspire_db.get_inspire(source, id)`） → miss 時呼叫 API 取 content/tags/difficulty → LLM inspire → 儲存快取（`source`, `id`）
  - `action == "similar"`: 呼叫 `bot.api.search_similar_by_id(source, id, top_k, min_similarity)`
- [x] 統一錯誤處理（所有 action 共用）：
  - `ApiProcessingError` → ephemeral followup「資料準備中，請稍後重試」
  - `ApiNetworkError` → ephemeral followup「API 連線失敗，請稍後重試」
  - `ApiRateLimitError` → ephemeral followup「請求頻率過高，請稍後重試」
  - `ApiError` → ephemeral followup「查詢失敗」+ log error（含 endpoint/source/id）
  - `None` 回傳 → ephemeral followup「找不到題目」
- [x] 保留 `config_reset_*` handler
- [x] 保留 `user_sub_prev_*` / `user_sub_next_*` handler（/recent 用）
- [x] submission detail enrichment: `_get_submission_details()` 改用 `bot.api.resolve(slug)` 取得題目資訊
  - `resolve()` 回傳完整 problem dict 時直接使用，不再發起第二次 `get_problem()` 請求
  - `resolve()` 回傳 None 時，enrichment 欄位留空，不阻斷顯示

## Phase 3: Command Migration

### T6: Migrate /daily command
- [x] `cogs/slash_commands_cog.py` `daily_command()`:
  - 改呼叫 `bot.api.get_daily("com", date_str)`
  - 處理 `ApiProcessingError` → 回傳「資料準備中，請稍後重試」
  - 處理 `ApiRateLimitError` → 回傳「請求頻率過高，請稍後重試」
  - 處理 `None` 回傳 → 回傳「找不到該日期的每日挑戰」
- [x] `get_daily_history()`:
  - 改為使用 `asyncio.gather()` 並行呼叫 `bot.api.get_daily("com", d) for d in generate_history_dates(date)`
  - 併發上限：`asyncio.Semaphore(5)`
  - 404 的日期跳過（回傳 None）
- [x] `/daily_cn` 遷移至 API:
  - 改呼叫 `bot.api.get_daily("cn", date_str)`
  - 錯誤處理與 `/daily` 相同
  - 歷史查詢同樣使用 `domain="cn"`

### T7: Migrate /problem command
- [x] `cogs/slash_commands_cog.py` `problem_command()`:
  - 移除 `source_detector` import 和 `_detect_source()` 呼叫
  - **單題模式**：改用 `bot.api.resolve(query)` 智慧解析（支援 URL、slug、ID）
    - resolve 成功 → 使用回傳的 `problem` dict（直接使用，不再呼叫 `get_problem()`）
    - resolve 失敗 → 嘗試 `bot.api.get_problem("leetcode", query)`
    - 全部失敗 → 回傳「找不到題目」
  - **多題模式**（逗號分隔 `problem_ids`）：
    - 拆分 ID 列表，使用 `asyncio.gather()` 並行呼叫 API
    - 併發上限：`asyncio.Semaphore(5)`
    - 每個 ID 依序嘗試 `api.resolve(query)` → fallback `api.get_problem("leetcode", id)`
    - 單題成功 → `create_problem_embed()` + `create_problem_view()`
    - 多題成功 → `create_problems_overview_embed()` + `create_problems_overview_view()`
    - 部分失敗 → 成功的題目正常顯示，失敗的在 embed 中標註
  - `domain` 參數：保留，語意為 LeetCode content 語言偏好（非 LeetCode source 忽略）
  - `title`、`message` 參數：不受遷移影響，直接傳遞至 embed
  - `ApiProcessingError` → 回傳「資料準備中，請稍後重試」
  - `ApiNetworkError` → 回傳「API 連線失敗，請稍後重試」
  - `ApiError` → 回傳「查詢失敗」+ log error
- [x] 移除 `problems_db.get_problem()` 呼叫

### T8: Migrate /similar command
- [x] `cogs/similar_cog.py` 完全重寫：
  - 移除所有 embedding storage/searcher/generator/rewriter import
  - `/similar id:1 source:leetcode` → `bot.api.search_similar_by_id(source, id, top_k, min_similarity)`
  - `/similar query:"two sum"` → `bot.api.search_similar_by_text(query, source, top_k, min_similarity)`
  - top_k 和 min_similarity 從 config `[similar]` section 讀取
  - 結果 embed 建構：直接使用 API 回傳的 title/difficulty/link/similarity
  - `rewritten_query` null → 不顯示 footer；有值 → 顯示在 embed footer
  - 空結果 → 回傳「找不到相似題目」
  - `ApiProcessingError` → 回傳「資料準備中，請稍後重試」
  - `ApiNetworkError` → 回傳「API 連線失敗，請稍後重試」
  - `ApiError` → 回傳「查詢失敗」+ log error
- [x] 移除 `__init__` 中的 storage/searcher 初始化

### T9: Migrate schedule_manager_cog.py
- [x] `send_daily_challenge_job()`:
  - 改呼叫 `bot.api.get_daily("com")` 取得今日挑戰
  - 處理 `ApiProcessingError`：自動重試最多 3 次（間隔 2s → 4s → 8s，含 ±0.5s jitter）
    - 3 次皆 202 → log warning，本次不發送
  - 處理 `ApiRateLimitError` → log warning，不發送
  - 處理 `None` → log error
- [x] 移除對 `bot.lcus.get_daily_challenge()` 的呼叫

## Phase 3.5: Verification

### T15: Verify all migrated commands and buttons
- [x] `/daily` 正常顯示今日題目（資料來自 API）
- [x] `/daily date:2025-01-01` 正常顯示歷史題目
- [x] `/daily_cn` 正常顯示力扣每日一題（資料來自 API，`domain=cn`）**[SKIP: 後端 API 問題]**
- [x] `/problem problem_ids:1` 和 `/problem problem_ids:two-sum` 正常顯示題目
- [x] `/problem problem_ids:1,2,3` 多題概覽正常顯示，detail 按鈕運作正常
- [x] `/problem` 支援 Codeforces 和 AtCoder 題目（如 `/problem problem_ids:codeforces.com/contest/1/problem/A`）
- [x] `/problem` 的 `title` 和 `message` 參數正常傳遞至 embed
- [x] `/similar problem: 1` 和 `/similar query:two sum` 正常顯示相似題目
- [x] `/recent username` 正常顯示最近提交（保留直連 `LeetCodeClient.fetch_recent_ac_submissions()`）
- [x] `/recent` submission enrichment 正確使用 `bot.api.resolve()` 取得 rating/tags
- [x] Description/Translate/Inspire/Similar button 全部正常運作
- [x] Overview detail 按鈕（`problem|{source}|{id}|desc`）正常運作
- [x] Submission view 中的描述/翻譯/靈感按鈕正常運作
- [x] 排程系統正常發送每日挑戰
- [x] API 不可用時各命令回傳友善錯誤訊息（不崩潰）
- [x] 舊格式 button custom_id 被靜默忽略
- [x] LLM 翻譯/靈感在 cache DROP 後可正常重新生成

## Phase 4: Cleanup

### T10: Slim down leetcode.py
- [x] 移除 `fetch_category_problems()`, `_parse_problems()`
- [x] 移除 `init_all_problems()`
- [x] 移除 `fetch_problem_detail()`, `get_problem()`, `get_problem_rating()`
- [x] 移除 `fetch_ratings()`, `RATINGS_URL`, ratings 記憶體快取
- [x] 移除 `fetch_daily_challenge()`, `get_daily_challenge()`（統一使用 API）
- [x] 移除 `fetch_monthly_daily_challenges()`, `_process_remaining_monthly_challenges()`
- [x] 移除 `_level_to_name()`
- [x] 移除 semaphore、background task tracking、`shutdown()`
- [x] 移除 `problems_db`、`daily_db` 參數和引用
- [x] 精簡 `__init__`：僅保留 domain、graphql_url、session config
- [x] 保留：`fetch_recent_ac_submissions()`、`html_to_text()`、`generate_history_dates()`

### T11: Remove unused DB managers from database.py + Rebuild LLM cache
- [x] 移除 `ProblemsDatabaseManager` class（lines 173-528）
- [x] 移除 `DailyChallengeDatabaseManager` class（lines 860-982）
- [x] 移除 `EmbeddingDatabaseManager` class（lines 531-631）
- [x] `LLMTranslateDatabaseManager`:
  - [x] DROP 舊表 `llm_translate_results`（**注意**：所有現存翻譯快取將丟失，見 R6）
  - [x] 重建：PK `(source TEXT, problem_id TEXT)`，移除 `domain` 欄位
  - [x] 更新 `get_translation(source, problem_id)` 簽名
  - [x] 更新 `save_translation(source, problem_id, ...)` 簽名
- [x] `LLMInspireDatabaseManager`:
  - [x] DROP 舊表 `llm_inspire_results`（**注意**：所有現存靈感快取將丟失，見 R6）
  - [x] 重建：PK `(source TEXT, problem_id TEXT)`，移除 `domain` 欄位
  - [x] 更新 `get_inspire(source, problem_id)` 簽名
  - [x] 更新 `save_inspire(source, problem_id, ...)` 簽名
- [x] 保留 `SettingsDatabaseManager`
- [x] 清理 imports

### T12: Remove embeddings system
- [x] 刪除 `embeddings/` 目錄（generator.py, rewriter.py, searcher.py, storage.py, __init__.py）
- [x] 刪除 `embedding_cli.py`
- [x] 刪除 `data/migrate_embeddings.sql`（若存在）

### T13: Remove standalone OJ clients
- [x] 刪除 `codeforces.py`（若存在）
- [x] 刪除 `atcoder.py`（若存在）
- [x] 移除 bot.py 中對這些 client 的 import 和初始化

### T14: Clean up config
- [x] `config.toml.example`:
  - 移除 `[llm.gemini.models.embedding]` section
  - 移除 `[llm.gemini.models.rewrite]` section
  - 移除 `[leetcode]` 中的 `monthly_fetch_delay`
  - 新增 `[api]` section（T2 已完成）
- [x] `utils/config.py`: 移除 embedding/rewrite model 的讀取方法
- [x] 更新 `[logging.modules]` 移除不再需要的模組 logger

### T16: Remove source_detector.py + Clean up legacy files
- [x] 刪除 `utils/source_detector.py`（`api.resolve()` 已取代其功能，見 TD-13）
- [x] 移除所有對 `source_detector` 的 import（`slash_commands_cog.py`、`interaction_handler_cog.py` 等）
- [x] 清理 legacy daily challenge 檔案快取：
  - 刪除 `data/com/daily/` 目錄（若存在）
  - 刪除 `data/cn/daily/` 目錄（若存在）
  - 或在 README/changelog 中標註使用者可手動刪除
- [x] 刪除 `data/migrate_settings.sql`（若不再需要）
