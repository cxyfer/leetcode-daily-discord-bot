# Proposal: Migrate problem data layer to oj-api-rs

## Context

### User Need
v2.0 的核心變更：將 problems 相關的爬取、查詢、搜尋從 bot 內建的 LeetCode GraphQL 直連，替換為呼叫外部 REST API（oj-api-rs，部署於 `https://oj-api.gdst.dev/api/v1/*`）。目標是將題目資料層與 Discord bot 解耦。

### Current Implementation Constraints

**C1: LeetCodeClient 直連 LeetCode API** (leetcode.py:158-1010)
- 6 個 GraphQL/REST 呼叫函式直接存取 LeetCode 端點
- 內建 retry、backoff、semaphore 並行控制
- 本地 SQLite 快取 problems 和 daily_challenge 表
- ratings 從 GitHub TSV 檔案取得，有記憶體快取 (TTL 1hr)

**C2: ProblemsDatabaseManager** (utils/database.py:173-528)
- 本地 problems 表：composite PK `(source, id)`，17 個欄位
- 提供 `update_problems`、`update_problem`、`get_problem` 等 CRUD
- tags/similar_questions 以 JSON 字串存儲

**C3: DailyChallengeDatabaseManager** (utils/database.py:860-982)
- 本地 daily_challenge 表：PK `(date, domain)`
- 完整題目資料冗餘存儲（與 problems 表結構幾乎相同）

**C4: Embedding/Similar 系統** (embeddings/*, cogs/similar_cog.py)
- 本地 sqlite-vec 向量搜尋
- 需要 problem content 做 rewrite → embed pipeline
- `embedding_cli.py` 管理索引建構

**C5: LLM 系統** (llms/*, cogs/interaction_handler_cog.py)
- 翻譯和靈感功能需要 problem content（HTML）
- 透過 `html_to_text()` 轉換後送入 LLM
- 快取在 llm_translate_results / llm_inspire_results 表

**C6: /recent 命令** (leetcode.py:794-874, cogs/slash_commands_cog.py:524-592)
- 直接呼叫 LeetCode GraphQL `recentAcSubmissions`
- API 無對應端點，需保留直連

**C7: /daily_cn 命令** (cogs/slash_commands_cog.py:95-147)
- ~~使用 `bot.lccn` (domain=cn) 取得力扣每日一題~~
- ~~API 的 CN daily 資料尚未爬取，需保留直連~~
- **UPDATE**: API 已支援 `GET /api/v1/daily?domain=cn`，統一使用 API 取得

**C8: oj-api-rs API 回應格式** (已驗證)
- `GET /api/v1/problems/{source}/{id}` → 完整題目含 content、tags、rating
- `GET /api/v1/daily?domain=com&date=YYYY-MM-DD` → 完整 daily challenge
- `GET /api/v1/similar/{source}/{id}` → 向量相似搜尋（含 rewritten_query）
  - query params: `limit`, `threshold`, `source`（逗號分隔篩選）
- `GET /api/v1/similar?q=<text>&source=<filter>` → 文字查詢相似搜尋
  - query params: `q`（或 `query`）, `limit`, `threshold`, `source`
- `GET /api/v1/resolve/{query}` → URL/prefix/ID 智慧解析
- `GET /api/v1/tags/{source}` → 標籤列表
- 錯誤格式遵循 RFC 7807
- Bearer token 認證（可開關）

**C9: API 回應欄位與本地 schema 對照**
- API 回傳欄位：`id`, `source`, `slug`, `title`, `title_cn`, `difficulty`, `ac_rate`, `rating`, `contest`, `problem_index`, `tags` (array), `link`, `category`, `paid_only`, `content`, `content_cn`, `similar_questions` (array)
- 欄位集合與本地 problems 表一致，但 UI/內部表示需做少量正規化：
  - `title_cn` 空字串 → 視為 `None`（無中文標題）
  - `difficulty` null → 顯示 `"Unknown"`
  - `ac_rate` null → 預設 `0.0`
  - `rating` 為 `0.0` 時表示無 rating，不顯示
- Daily 端點額外回傳 `date`, `domain`
- Similar 端點回傳 `rewritten_query` + results array（含 `similarity` 分數）

## Requirements

### REQ-1: 新增 API client 模組
**Priority:** High

**Acceptance Criteria:**
- 新增 `api_client.py`，封裝所有 oj-api-rs REST API 呼叫
- 支援 `base_url` 和可選 `token` 配置（從 config.toml 讀取）
- 使用 `aiohttp` 進行非同步 HTTP 呼叫（bot 已有此依賴）
- 實作方法：`get_problem(source, id)`, `get_daily(domain, date)`, `search_similar_by_id(source, id, ...)`, `search_similar_by_text(query, ...)`, `resolve(query)`
- 錯誤處理：解析 RFC 7807 回應，轉換為適當的 Python 例外

**Constraints:**
- 不實作本地快取——API server 端已有快取機制
- 不實作 retry——保持 client 精簡，API server 端已有 crawler fallback（HTTP 202）
- `token` key 可完全省略；若存在則值可為空字串（視為無 token）

### REQ-2: 替換 /daily 命令的資料來源
**Priority:** High

**Acceptance Criteria:**
- `/daily` 和 `/daily date:YYYY-MM-DD` 改為呼叫 `GET /api/v1/daily?domain=com&date=`
- `get_daily_history()` 改為多次呼叫 daily API（逐日查詢歷史同日）
- 移除 COM domain 的 daily 舊流程：`fetch_monthly_daily_challenges()`、`_process_remaining_monthly_challenges()`
- 注意：`fetch_daily_challenge()` 僅移除 COM 路徑的呼叫，方法本身保留供 CN domain 使用（見 REQ-7 Constraints）
- 移除 `DailyChallengeDatabaseManager` 及 daily_challenge 表的使用

**Constraints:**
- ~~`/daily_cn` 保留直連 LeetCode CN GraphQL（C7）~~ **UPDATE**: 統一使用 API，`/daily_cn` 呼叫 `api.get_daily("cn", date)`
- API 回傳 HTTP 202 時需處理：提示使用者稍後重試
- `get_daily_history()` 的歷史日期查詢若 404 則跳過（該日無資料）

### REQ-3: 替換 /problem 命令的資料來源
**Priority:** High

**Acceptance Criteria:**
- `/problem` 改為呼叫 `GET /api/v1/problems/{source}/{id}` 或 `GET /api/v1/resolve/{query}`
- 支援 LeetCode、Codeforces、AtCoder 三個 source
- **多題模式**：逗號分隔的 `problem_ids` 仍須支援，使用 `asyncio.gather()` 並行呼叫 API，結果以 overview embed/view 呈現
- 移除 `fetch_category_problems()`、`fetch_problem_detail()`、`init_all_problems()`
- 移除 `fetch_ratings()` 及記憶體 ratings 快取
- 移除 `ProblemsDatabaseManager` 中僅被 LeetCodeClient 使用的方法

**Constraints:**
- LLM 功能（翻譯/靈感）仍需 problem content，改從 API 取得
- button handler 中的 `get_problem()` 呼叫全部改為 API client
- `html_to_text()` 保留——LLM 和 Discord 顯示仍需此轉換
- `/daily_cn` 同樣使用 API 取得資料（`domain=cn`）
- `/problem` 的 `domain` 參數在遷移後語意弱化（API 以 `source` 區分），需保留向後相容或移除並更新使用說明
- `title`、`message` 參數不受遷移影響，直接傳遞至 embed 建構

### REQ-4: 替換 /similar 命令的資料來源
**Priority:** High

**Acceptance Criteria:**
- `/similar` 改為呼叫 `GET /api/v1/similar/{source}/{id}` 或 `GET /api/v1/similar?q=<text>`
- 移除本地 embeddings/ 模組（generator, rewriter, searcher, storage）
- 移除 `EmbeddingDatabaseManager`
- 移除 `embedding_cli.py`
- interaction_handler_cog.py 中的 similar button 改為呼叫 API

**Constraints:**
- API 回傳的 similar results 已包含 `title`, `difficulty`, `link`，不需再查 DB enrichment
- `rewritten_query` 可選擇性顯示在 embed 中

### REQ-5: 替換 interaction handler 的資料來源
**Priority:** High

**Acceptance Criteria:**
- Description button：改從 API 取得 problem content
- Translate button：改從 API 取得 content → `html_to_text()` → LLM
- Inspire button：改從 API 取得 content/tags/difficulty → LLM
- Similar button：改呼叫 similar API
- External problem buttons（`ext_*`）：統一使用 API client

**Constraints:**
- LLM 快取表 schema 變更：`(problem_id INTEGER, domain TEXT)` → `(source TEXT, problem_id TEXT)`
- v2.0 大版本更新，直接 DROP 舊表重建（快取會在使用者點擊按鈕時重新生成）
- button custom_id 統一為 `problem|{source}|{id}|{action}`

### REQ-6: 配置更新
**Priority:** High

**Acceptance Criteria:**
- config.toml 新增 `[api]` section：`base_url`, `token`（可省略）, `timeout`（預設 10，單位秒）
- config.py 新增對應的讀取方法
- config.toml.example 更新範例

**Constraints:**
- 環境變數 override 保持一致（`API_BASE_URL`, `API_TOKEN`）

### REQ-7: 清理廢棄程式碼
**Priority:** Medium

**Acceptance Criteria:**
- 移除 `leetcode.py` 中不再使用的 GraphQL 查詢和 REST 呼叫（保留 `/recent` 和 `/daily_cn` 所需的部分）
- 移除 `ProblemsDatabaseManager`（若完全不再使用）
- 移除 `DailyChallengeDatabaseManager`
- 移除 `EmbeddingDatabaseManager`
- 移除 `embeddings/` 目錄和 `embedding_cli.py`
- 移除 `codeforces.py` 和 `atcoder.py`（題目資料改從 API 取得）
- 移除或精簡 `utils/source_detector.py`（`api.resolve()` 已取代大部分偵測邏輯）
- 清理 `bot.py` 中的初始化邏輯（移除 `lcus.init_all_problems()` 等）
- 清理 legacy daily challenge 檔案快取目錄 `data/{domain}/daily/`（或在文件中標註可手動刪除）

**Constraints:**
- `leetcode.py` 保留：`fetch_recent_ac_submissions()`、`html_to_text()`、`generate_history_dates()`
- ~~`fetch_daily_challenge()` (CN only)~~ **UPDATE**: CN daily 改由 API 提供，移除相關方法
- `SettingsDatabaseManager` 保留不變
- `LLMTranslateDatabaseManager` 和 `LLMInspireDatabaseManager` 保留，但 schema 變更：`(problem_id INTEGER, domain)` → `(source TEXT, problem_id TEXT)`
- `source_detector.py`：若 `api.resolve()` 完全覆蓋所有平台偵測（含 luogu、uva、spoj），則整檔刪除；否則保留 `detect_source()` 作為 `resolve()` 的前置輔助

### REQ-8: /recent 命令保留直連
**Priority:** High

**Acceptance Criteria:**
- `/recent` 繼續使用 `LeetCodeClient.fetch_recent_ac_submissions()`
- submission detail 的 enrichment（rating、tags 等）改從 API 取得

**Constraints:**
- `LeetCodeClient` 精簡為僅保留 submissions 和 CN daily 相關功能

## Success Criteria

### Functional
1. `/daily` 和 `/daily date:2025-01-01` 正常顯示題目（資料來自 API）
2. `/daily_cn` 正常顯示力扣每日一題（資料來自 API，`domain=cn`）
3. `/problem 1` 和 `/problem two-sum` 正常顯示題目（資料來自 API）
4. `/problem 1,2,3` 多題概覽正常顯示，detail 按鈕正常運作
5. `/problem` 支援 Codeforces 和 AtCoder 題目
5. `/similar 1` 和 `/similar query:two sum` 正常顯示相似題目（資料來自 API）
6. `/recent username` 正常顯示最近提交（保留直連）
7. Description/Translate/Inspire/Similar button 全部正常運作
8. 排程系統正常發送每日挑戰

### Technical
1. `api_client.py` 為唯一的 oj-api-rs 存取點
2. 本地不再存儲 problems、daily_challenge、embeddings 資料
3. `leetcode.py` 僅保留 submissions、CN daily、`html_to_text()` 相關功能
4. config.toml 包含 `[api]` section
5. 無 import 殘留、無未使用的 DB manager

## Design Decisions

### D1: 不實作本地快取
**Rationale:** API server 端已有 SQLite 快取和 crawler fallback 機制。bot 端加快取會造成雙重快取的一致性問題。LLM 快取保留是因為 LLM 呼叫成本高且結果不會變。

### ~~D2: /daily_cn 保留直連~~ **DEPRECATED**
~~**Rationale:** API 的 CN daily 資料尚未爬取（測試回傳 404）。保留直連確保功能不中斷，未來 API 支援後可再遷移。~~

**UPDATE**: API 已支援 `GET /api/v1/daily?domain=cn`。`/daily_cn` 統一使用 API，`domain=cn` 參數區分來源。

### D3: /recent 保留直連
**Rationale:** API 無 user submissions 端點。此功能與「題目資料」本質不同（是使用者行為資料），保留在 bot 端合理。

### D4: 移除本地 embedding 系統
**Rationale:** API 已提供完整的向量相似搜尋（by ID 和 by text），且使用相同的 Gemini embedding 模型。本地維護 sqlite-vec 索引不再必要。

### D5: 移除月度批次回填機制
**Rationale:** API 的 `/daily?date=` 已能直接查詢任意歷史日期，不需要 bot 端批次回填整月資料。

### D6: LeetCodeClient 精簡而非移除
**Rationale:** 仍需保留 `fetch_recent_ac_submissions()`。完全移除會導致 `/recent` 功能需要重寫。精簡後的 client 僅保留必要的 GraphQL 呼叫。

**UPDATE**: CN daily 已遷移至 API，`fetch_daily_challenge()` 可完全移除。

## Dependencies

### Internal
- `api_client.py`（新增）：所有 cog 的主要資料來源
- `leetcode.py`：精簡，保留 submissions + CN daily + html_to_text
- `utils/config.py`：新增 API 配置讀取
- `cogs/slash_commands_cog.py`：資料來源切換
- `cogs/interaction_handler_cog.py`：資料來源切換
- `cogs/similar_cog.py`：完全重寫為 API 呼叫
- `cogs/schedule_manager_cog.py`：daily challenge 來源切換
- `utils/ui_helpers.py`：可能需微調 embed 建構（API 回應格式略有不同）
- `bot.py`：初始化邏輯調整

### External
- oj-api-rs API：`https://oj-api.gdst.dev/api/v1/*`
- API 可用性為硬依賴——API 不可用時 bot 的題目功能將無法運作

### Risks
- **R1: API 可用性** → bot 功能依賴外部 API。Mitigation: health check 端點監控；API 部署於 Zeabur 有自動重啟。
- **R2: API 回應延遲** → 可能影響 Discord 3 秒回應限制。Mitigation: 使用 `defer()` 延遲回應。
- **R3: ~~CN daily 資料缺口~~** → ~~API 未來支援 CN 時需要二次遷移。Mitigation: 保持 LeetCodeClient CN 相關程式碼獨立，方便未來移除。~~ **RESOLVED**: API 已支援 `domain=cn`
- **R4: HTTP 202 處理** → daily API 可能回傳 202（crawler 正在爬取）。Mitigation: 向使用者顯示「資料準備中，請稍後重試」訊息。
- **R5: API schema 變動** → API 回傳格式變動時 bot 可能崩潰。Mitigation: api_client 對關鍵欄位（`id`, `source`, `link`）做存在性檢查，缺失時 raise `ApiError`。
- **R6: LLM 快取 Drop & Rebuild 資料遺失** → v2.0 DROP 舊表重建，所有現存翻譯和靈感快取將永久丟失。Impact: 使用者首次點擊按鈕需等待 LLM 重新生成（增加短期 API 呼叫量）。Mitigation: v2.0 為重大版本更新，可接受；快取會隨使用者互動逐步重建。
