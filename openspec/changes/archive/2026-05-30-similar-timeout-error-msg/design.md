## Context

目前 `OjApiClient` 使用 session-level `aiohttp.ClientTimeout(total=10)` 作為所有 API 請求的 timeout。`/similar` 查詢走的是遠端 embedding 比對，後端可能需要數十秒甚至上百秒才能回應。10 秒 timeout 不僅導致大部分 similar 請求失敗，更糟糕的是失敗後使用者只看到「API 連線失敗」，無法區分是 timeout、embedding 掛了、還是 query 格式有問題。

後端 OpenAPI spec 已明確定義 per-endpoint 的錯誤碼：

| Endpoint | 成功 | 錯誤碼 |
|----------|:----:|--------|
| `POST /similar` (文字) | 200 | 400, 502, 504 |
| `GET /similar/{source}/{id}` (題目) | 200 | 404, 500 |

這些錯誤碼目前被 `_do_request` 統一轉成 `ApiError(status, detail)`，cog 層只 catch `ApiError` 並顯示通用的「查詢失敗」。

## Goals / Non-Goals

**Goals:**
- Similar 查詢使用獨立可設定的 timeout，預設 300 秒
- Per-request timeout 覆蓋 session 層級，不影響其他 API 呼叫
- 使用者能從錯誤訊息判斷是 timeout、embedding 不可用、還是 query 格式問題
- `SimilarConfig` 成為 timeout 設定的 single source of truth
- Config 和 EnvConfig 兩條路徑都支援

**Non-Goals:**
- 不修改其他 API endpoint 的 timeout 行為
- 不加類似 inspire 的 caching 或 dedup 機制（那是獨立的改善）
- 不修改後端 API 行為
- 不引入 202 polling/retry 邏輯（後端 similar 目前不定義 202）

## Decisions

### Decision 1: Per-request timeout via `aiohttp.ClientTimeout` override

`aiohttp` 的 `session.request(timeout=...)` 接受 `ClientTimeout` 物件覆蓋 session 層級的 timeout。這比修改 session 層級 timeout 更精確，因為只影響 similar 請求。

```python
# session 層級 (現有，不變)
self._session = aiohttp.ClientSession(timeout=ClientTimeout(total=10))

# per-request 覆蓋 (新增)
timeout = aiohttp.ClientTimeout(total=cfg.timeout)
await self._session.request("GET", path, timeout=timeout)
```

**Alternatives considered:**
- **修改 session 層級 timeout**：太粗暴，所有 API 呼叫都受影響
- **建立第二個 session**：多餘的複雜度，aiohttp 原生支援 per-request override
- **用 asyncio.wait_for 包裝**：可行但不夠精確，無法區分 connect/read/total timeout

### Decision 2: 新增獨立的例外類別（flat，遵循現有慣例）

在 `api_client.py` 新增兩個例外，與現有 `ApiProcessingError`、`ApiRateLimitError` 同層級（非繼承關係）：

```python
class ApiEmbeddingError(ApiError):        # 502
class ApiEmbeddingTimeoutError(ApiError):  # 504
```

Wait — 現有慣例是 flat（`ApiProcessingError` 直接繼承 `Exception`），但讓新例外繼承 `ApiError` 有一個好處：現有的 `except ApiError` catch 不會漏掉。但我們正是要區分這些錯誤，所以應該讓它們**不**繼承 `ApiError`。這樣 cog 層可以先 catch 特定例外，fallback 到 `ApiError`。

**修正**：遵循現有 flat 慣例，直接繼承 `Exception`：

```python
class ApiEmbeddingError(Exception):       # 502
class ApiEmbeddingTimeoutError(Exception): # 504
```

**Alternatives considered:**
- **在 cog 層檢查 `ApiError.status`**：簡單但把 HTTP 狀態碼知識洩漏到 cog 層
- **繼承 ApiError**：會被 generic `except ApiError` 吃掉，失去區分效果

### Decision 3: `_request` 簽章新增 `timeout` keyword

`_do_request` 已經用 `**kwargs` 透傳給 `session.request()`，所以 `timeout` 會自然傳遞到 aiohttp。只需修改 `_request` 簽章和 dedup key 的計算：

```python
async def _request(self, method, path, *, timeout=None, **kwargs):
    # timeout 不參與 dedup key（相同請求不同 timeout 仍應合併）
    ...
    result = await self._do_request(method, path, timeout=timeout, **kwargs)
```

`timeout` 不應參與 inflight dedup key，因為兩個相同請求只是 timeout 不同，仍應共用同一個 in-flight future。

### Decision 4: Config 預設值策略

| 設定路徑 | 值 | 說明 |
|----------|-----|------|
| `config.toml` → `[similar].timeout` | `300` | 主要設定來源 |
| `EnvConfig.get_similar_config()` | 沿用 `SimilarConfig()` 預設 | .env fallback 路徑 |
| `SimilarConfig(timeout=300)` | `300` | dataclass default |

不引入 `SIMILAR_TIMEOUT` 環境變數，保持 EnvConfig 簡單。真的有需要可以直接改 `config.toml`。

## Risks / Trade-offs

- **[Risk] 300 秒預設可能仍不夠** → 後端 504 有自己的 timeout，但 client 端至少要等得比 server 端久。300 秒覆蓋大部分情境，且值可設定
- **[Risk] 長時間 timeout 占用 connection pool** → similar 請求量不高（user-initiated），且 TCPConnector 已設 limit=50，不至於枯竭
- **[Risk] Discord interaction 15 分鐘 window** → `defer()` 後有 15 分鐘，300 秒遠在此範圍內，安全
- **[Trade-off] inflight dedup key 不納入 timeout** → 如果兩個用戶同時發起相同 similar 請求但不同 timeout，會共用第一個的 timeout。極端邊緣案例，不值得為此拆分
