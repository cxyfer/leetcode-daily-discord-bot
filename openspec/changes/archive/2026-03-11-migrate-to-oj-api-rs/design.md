# Design: Migrate problem data layer to oj-api-rs

## Technical Decisions

### TD-1: API Client 架構
- 新增 `api_client.py`，單一 class `OjApiClient`
- 使用 `aiohttp.ClientSession`（shared, long-lived），bot 啟動時建立、關閉時銷毀
  - Connector: `aiohttp.TCPConnector(limit=50, limit_per_host=10, keepalive_timeout=30)`
- 不實作 TTL 本地快取
- **Singleflight**：同一 `(method, path, params)` 的並發請求共用同一 `asyncio.Future`，僅發出一次 HTTP 請求
  - 實作：`dict[str, asyncio.Future]`，key 為 `f"{method}:{path}?{sorted_params}"`
  - 請求完成後立即從 dict 移除（無 TTL）
- 錯誤處理：
  - HTTP 200 → 回傳 JSON dict
  - HTTP 404 → `None`
  - HTTP 202 → raise `ApiProcessingError(detail)`（上層決定是否重試）
  - HTTP 429 → 讀取 `Retry-After` header（秒數），`await asyncio.sleep(retry_after)`，重試一次；第二次 429 → raise `ApiRateLimitError(retry_after)`
  - 其他 4xx/5xx → `ApiError(status, detail)`（解析 RFC 7807 body）
  - `asyncio.TimeoutError` / `aiohttp.ClientError` → `ApiNetworkError(str(e))`
  - JSON decode 失敗 → `ApiError(status, "Invalid response body")`
- Bearer token 透過 `Authorization` header 傳遞（可選）
- Exception classes: `ApiError(status, detail)`, `ApiProcessingError(detail)`, `ApiNetworkError(detail)`, `ApiRateLimitError(retry_after)`

### TD-2: Button custom_id 統一格式
- 所有題目按鈕統一為：`problem|{source}|{id}|{action}`
  - action: `desc`, `translate`, `inspire`, `similar`
  - 範例：`problem|leetcode|1|desc`, `problem|codeforces|1A|inspire`
- 移除 `leetcode_problem_*`, `leetcode_translate_*`, `leetcode_inspire_*`, `leetcode_similar_*` 前綴
- 移除 `ext_problem|*`, `ext_translate|*`, `ext_inspire|*`, `ext_similar|*` 前綴
- InteractionHandlerCog 改為單一 `on_interaction` 解析統一格式
- 遇到舊格式 custom_id（不符合 `problem|*` 模式）時靜默忽略（僅 debug log），不拋出例外
- v2.0 為重大版本，舊按鈕失效可接受

### TD-3: Config 結構
```toml
[api]
base_url = "https://craboj.zeabur.app/api/v1"
# token = "your_api_token_here"  # Optional
timeout = 10
```
- 環境變數 override：`API_BASE_URL`, `API_TOKEN`
- 移除 `[llm.gemini.models.embedding]` 和 `[llm.gemini.models.rewrite]`
- 保留 `[similar]` section（top_k, min_similarity 作為 API 查詢參數）
- 移除 `[leetcode]` 中的 `monthly_fetch_delay`（不再需要月度回填）

### TD-4: LeetCodeClient 精簡
保留：
- `__init__`（精簡，移除 problems_db/ratings/daily_db 相關）
- ~~`fetch_daily_challenge()`（僅 CN domain 使用）~~ **REMOVED**: CN daily 改由 API 提供
- ~~`get_daily_challenge()`（僅 CN domain 使用，精簡為只查 API 或直連）~~ **REMOVED**: 統一使用 `api.get_daily("cn")`
- `fetch_recent_ac_submissions()`
- `html_to_text()`（靜態方法，LLM 和 Discord 顯示仍需）
- `generate_history_dates()`（靜態方法）

移除：
- `fetch_category_problems()`, `_parse_problems()`, `init_all_problems()`
- `fetch_problem_detail()`, `get_problem()`, `get_problem_rating()`
- `fetch_ratings()`, ratings 記憶體快取
- ~~`fetch_daily_challenge()`, `get_daily_challenge()`~~ **ADDED**: 統一使用 API
- `fetch_monthly_daily_challenges()`, `_process_remaining_monthly_challenges()`
- `_level_to_name()`（API 已回傳字串 difficulty）
- 所有 semaphore/background task 管理（不再需要並行爬取）

**NOTE:** 精簡後 `leetcode.py` 僅剩 3 個函式。`html_to_text()` 和 `generate_history_dates()` 本質上與 LeetCode 無關（通用工具），後續版本可考慮遷移至 `utils/`。本次遷移不做此重構，避免擴大變更範圍。

### TD-5: Database 精簡
保留：
- `SettingsDatabaseManager`（伺服器設定）
- `LLMTranslateDatabaseManager`（LLM 翻譯快取，schema 變更見 TD-9）
- `LLMInspireDatabaseManager`（LLM 靈感快取，schema 變更見 TD-9）

移除：
- `ProblemsDatabaseManager`（題目資料改從 API 取得）
- `DailyChallengeDatabaseManager`（daily 資料改從 API 取得）
- `EmbeddingDatabaseManager`（embedding 改從 API 取得）

### TD-6: /recent submission enrichment
- `_get_submission_details()` 中的 `lcus.get_problem(slug=slug)` 改為 `api.resolve(slug)`
- `resolve()` 回傳完整 problem dict 時直接使用，不再發起第二次 `get_problem()` 請求
- `resolve()` 回傳 None 時，enrichment 欄位（rating、tags）留空，不阻斷顯示

### TD-7: Daily challenge 資料流
- `/daily`（COM）：`api.get_daily("com", date)` → 直接回傳完整題目
- `/daily_cn`（CN）：`api.get_daily("cn", date)` → 統一使用 API
- 排程發送：`send_daily_challenge_job()` 改呼叫 `api.get_daily("com")`
- `get_daily_history()`：改為使用 `asyncio.gather()` 並行呼叫 `api.get_daily(domain, date)` 逐日查詢
  - 併發上限：`asyncio.Semaphore(5)`
  - Singleflight 會自動合併相同 date 的請求
  - COM 和 CN domain 各自獨立查詢

### TD-9: LLM Cache Schema 變更（Drop & Rebuild）
- v2.0 大版本更新，直接 DROP 舊表重建
- **影響**：所有現存翻譯和靈感快取將永久丟失（見 R6）
- 快取會在使用者點擊按鈕時透過 LLM 重新生成；短期內 API 呼叫量會增加
- 新 schema：
  ```sql
  -- llm_translate_results
  source TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  translation TEXT,
  created_at INTEGER NOT NULL,
  model_name TEXT,
  PRIMARY KEY (source, problem_id)

  -- llm_inspire_results
  source TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  thinking TEXT,
  traps TEXT,
  algorithms TEXT,
  inspiration TEXT,
  created_at INTEGER NOT NULL,
  model_name TEXT,
  PRIMARY KEY (source, problem_id)
  ```
- `domain` → `source`：統一使用 API source 欄位（如 `"leetcode"`, `"codeforces"`）
- `problem_id` 從 `INTEGER` 改為 `TEXT`：支援非數字 ID（如 `"1A"`, `"abc100_a"`）
- CN daily 的題目亦使用 `source="leetcode"`（同一題目，同一快取）
- LLM 快取會在使用者點擊按鈕時重新生成

### TD-10: HTTP 202 混合策略
- **排程發送**（`send_daily_challenge_job`）：自動重試最多 3 次
  - 間隔：2s → 4s → 8s（含隨機 jitter ±0.5s）
  - 3 次皆 202 → log warning，不發送
- **使用者命令/按鈕**：不自動重試，直接回覆 ephemeral「資料準備中，請稍後重試」
- 重試邏輯封裝在呼叫端，不在 `OjApiClient` 內（client 只拋 `ApiProcessingError`）

### TD-11: 所有 API 依賴按鈕必須 defer()
- Description、Translate、Inspire、Similar 四個 action 全部在處理前先 `await interaction.response.defer(ephemeral=True)`
- 回覆改用 `interaction.followup.send()`
- `defer()` 本身置於 `try/except discord.HTTPException` 內，失敗時 log warning 並 return

### TD-8: Similar search 資料流
- `/similar id:1`：`api.search_similar_by_id("leetcode", "1", top_k, min_similarity)`
  - API query params 映射：`top_k` → `limit`, `min_similarity` → `threshold`
- `/similar query:"two sum"`：`api.search_similar_by_text("two sum", source, top_k, min_similarity)`
  - API query params 映射：`query` → `q`, `top_k` → `limit`, `min_similarity` → `threshold`
- API 回傳已包含 title/difficulty/link，不需額外查詢
- `rewritten_query` 顯示在 embed footer

### TD-12: /problem 多題概覽流程
- 使用者輸入 `/problem problem_ids:1,2,3` 時，拆分 ID 後使用 `asyncio.gather()` 並行呼叫 API
  - 每個 ID 依序嘗試 `api.resolve(query)` → fallback `api.get_problem("leetcode", id)`
  - 併發上限：`asyncio.Semaphore(5)`（與 daily_history 一致）
- 單題結果 → 使用 `create_problem_embed()` + `create_problem_view()`
- 多題結果 → 使用 `create_problems_overview_embed()` + `create_problems_overview_view()`
- Overview detail 按鈕格式統一為 `problem|{source}|{id}|desc`（取代舊 `problem_detail|*` 和 `problem_detail_*`）
- 部分查詢失敗時：成功的題目正常顯示，失敗的題目在 embed 中標註「查詢失敗」
- `/problem` 的 `domain` 參數：遷移後僅影響 LeetCode source 的 content 語言偏好，非 LeetCode source 忽略此參數
- `problem_domain_autocomplete`：保留現有行為（com/cn），語意調整為 content 語言偏好

### TD-13: source_detector.py 處置
- `api.resolve()` 已能解析 URL、slug、prefix:id 格式，涵蓋 `source_detector.py` 的大部分功能
- **處置策略**：Phase 4 移除 `source_detector.py`
  - `resolve()` 已支援的平台：leetcode, codeforces, atcoder（API 有資料的平台）
  - `resolve()` 不支援的平台（luogu, uva, spoj）：API 無這些平台的資料，偵測後也無法查詢，移除合理
  - `/problem` 中的 `source` 參數仍可由使用者手動指定 source，作為 `resolve()` 的補充
- 若未來 API 新增平台支援，`resolve()` 自動涵蓋，無需 bot 端更新

## Data Model Mapping

### API Problem Response → Internal Dict
| API 欄位 | 型別 | 內部欄位 | 轉換 |
|---|---|---|---|
| `id` | string | `id` | 無（原本也是 string） |
| `source` | string | `source` | 無 |
| `slug` | string | `slug` | 無 |
| `title` | string | `title` | 無 |
| `title_cn` | string | `title_cn` | `""` → `None`（統一空值處理） |
| `difficulty` | string\|null | `difficulty` | null → `"Unknown"` |
| `ac_rate` | float\|null | `ac_rate` | null → `0.0` |
| `rating` | float | `rating` | `0.0` 表示無 rating |
| `contest` | string\|null | `contest` | 無 |
| `problem_index` | string\|null | `problem_index` | 無 |
| `tags` | array[string] | `tags` | 無（已是 list） |
| `link` | string | `link` | 無 |
| `category` | string | `category` | 無 |
| `paid_only` | int | `paid_only` | 無 |
| `content` | string\|null | `content` | 無（HTML 格式） |
| `content_cn` | string\|null | `content_cn` | 無 |
| `similar_questions` | array | `similar_questions` | 無（已是 list） |

### API Daily Response → Internal Dict
- 額外欄位：`date` (string), `domain` (string)
- 其餘與 Problem 相同

### API Similar Response
```json
{
  "rewritten_query": "string|null",
  "results": [
    {
      "source": "string",
      "id": "string",
      "title": "string",
      "difficulty": "string|null",
      "link": "string",
      "similarity": float
    }
  ]
}
```
- `rewritten_query` null → 不顯示 footer
- `difficulty` null → 顯示 `"Unknown"`
- `results` 空陣列 → 顯示「找不到相似題目」
- `similarity` 保留兩位小數顯示

### API Resolve Response
```json
{
  "source": "string",
  "id": "string",
  "problem": { /* 完整 Problem dict，同 API Problem Response */ }
}
```
- 回傳 404 → `None`（query 無法解析）
- `problem` 欄位包含完整題目資料，可直接使用，無需再呼叫 `get_problem()`

## Dependency Graph (Implementation Order)

```
Phase 1: Foundation
  T1: api_client.py (新增，無依賴)
  T2: config.py + config.toml (API 配置)

Phase 2: Core Migration
  T3: bot.py (初始化 api client，依賴 T1+T2)
  T4: ui_helpers.py (統一 button custom_id + 全面適配，依賴 T3)
  T5: interaction_handler_cog.py (統一 button 解析，依賴 T3+T4)

Phase 3: Command Migration
  T6: slash_commands_cog.py /daily (依賴 T3)
  T7: slash_commands_cog.py /problem (含多題概覽，依賴 T3+T4)
  T8: similar_cog.py /similar (依賴 T3)
  T9: schedule_manager_cog.py (依賴 T3)

Phase 3.5: Verification (所有 API consumer 完成後)
  T15: 驗證所有命令與按鈕功能 (依賴 T5+T6+T7+T8+T9)

Phase 4: Cleanup (依賴 T15 驗證通過)
  T10: leetcode.py 精簡 (依賴 T15)
  T11: database.py 移除 DB managers + LLM cache 重建 (依賴 T15)
  T12: 移除 embeddings/ + embedding_cli.py (依賴 T11)
  T13: 移除 codeforces.py + atcoder.py (依賴 T15)
  T14: config.toml 清理 (依賴 T10+T12)
  T16: 移除 source_detector.py + 清理 legacy files (依賴 T7+T15)
```

## PBT Properties (Property-Based Testing)

### PBT-1: Singleflight Idempotency
- **Invariant**: N 個併發呼叫 `_request("GET", "/daily", params={"domain":"com","date":"2025-01-01"})` 只發出恰好 1 次 HTTP 請求
- **Falsification**: Mock API 加入 100ms 延遲，啟動 10 個併發 coroutine，斷言 mock 被呼叫次數 == 1
- **Boundary**: 不同 params 的請求不共用（`date=2025-01-01` vs `date=2025-01-02` 各自獨立）

### PBT-2: API Error Isolation
- **Invariant**: 任何 `ApiError`/`ApiProcessingError`/`ApiNetworkError`/`ApiRateLimitError` 永遠不會以 unhandled exception 傳播到 Discord；所有 action handler 回傳 ephemeral 錯誤訊息
- **Falsification**: 對每個 action（desc/translate/inspire/similar），mock API 回傳各種錯誤碼（202/404/429/500/timeout），驗證 interaction.followup.send 被呼叫且 ephemeral=True

### PBT-3: Button ID Round-trip
- **Invariant**: `parse_button_id(format_button_id(source, id, action)) == (source, id, action)` 對任意合法 source/id/action 成立
- **Falsification**: 生成隨機 source（含 `-_`）、id（含數字和字母混合如 `"1A"`, `"abc_100"`）、action（`desc`/`translate`/`inspire`/`similar`），驗證 round-trip
- **Boundary**: `|` 字元不允許出現在 source/id 中（pipe 為分隔符）

### PBT-4: LLM Cache Consistency
- **Invariant**: `save(source, id, text)` 後 `get(source, id)` 回傳相同 text；不同 `(source, id)` 互不干擾
- **Falsification**: 隨機 source+id 對，save 後 get，斷言相等；交叉查詢其他 key 斷言 None

### PBT-5: HTTP 202 Retry Bounds
- **Invariant**: 排程模式最多重試 3 次，總等待時間 ≤ 20s（2+4+8+jitter）；命令模式重試 0 次
- **Falsification**: Mock API 永遠回傳 202，量測排程重試次數和耗時；驗證命令模式直接拋出 `ApiProcessingError`

### PBT-6: HTTP 429 Retry-After Compliance
- **Invariant**: 收到 429 + `Retry-After: N` 時，client 等待 ≥ N 秒後重試一次；第二次 429 → raise `ApiRateLimitError`
- **Falsification**: Mock 429 + `Retry-After: 2`，量測第二次請求的時間差 ≥ 2s；Mock 連續 429 驗證 raise

### PBT-7: Singleflight Key Isolation
- **Invariant**: 不同 `(method, path, params)` 的請求互不影響，回傳各自的結果
- **Falsification**: 併發呼叫 `get_daily("com", "2025-01-01")` 和 `get_daily("com", "2025-01-02")`（mock 回傳不同資料），驗證結果正確對應

### PBT-8: Graceful Degradation
- **Invariant**: API 不可達時，所有命令/按鈕在 timeout（10s）+ 處理時間內回覆使用者友善錯誤訊息，不崩潰
- **Falsification**: Mock API timeout，觸發所有 5 個命令和 4 個 action，驗證每個都回傳 ephemeral 錯誤且 bot 存活
