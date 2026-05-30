## Context

目前 `/random` 指令的 `tags` 參數是自由文字字串，無任何 autocomplete 輔助。`GET /api/v1/tags/{source}` 端點可回傳指定來源的有效標籤清單（字串陣列），需要 bearer auth。Discord.py 提供 `@<command>.autocomplete("param")` decorator 可為單一參數加上動態 autocomplete，且可以從 `interaction.namespace` 取得使用者已選擇的其他參數值。

現有前例：`@problem_command.autocomplete("domain")`（`slash_commands_cog.py:343`），但該案例是靜態資料。本次需要的是**根據 source 動態查詢**的 autocomplete。

## Goals / Non-Goals

**Goals:**
- 當使用者在 `/random` 選擇 source 後，在 `tags` 欄位輸入時自動顯示該來源的有效標籤建議
- 透過 TTL 快取避免重複請求 API，減少延遲與 API 負載
- API 失敗時 graceful degradation（回傳空清單或 stale cache），不影響主指令流程

**Non-Goals:**
- 不為 `difficulty` 或 `source` 參數增加 autocomplete（已是靜態 choices）
- 不支援跨來源的複合標籤查詢（API 本身以單一 source 為單位）
- 不實作管理員手動刷新快取的功能

## Decisions

### 1. Tags 快取放在 `OjApiClient`

**選擇**：在 `OjApiClient` 內部實作 `_tags_cache` 字典 + `get_tags_cached()` 方法。

**替代方案**：獨立的 `TagCache` 類別或 module-level global。

**理由**：Tags 資料與 API 端點緊密耦合，放在 API client 內部是最小驚訝原則。不需要引入新的模組或依賴注入。既有 `_inflight` dedup 機制也已在 `OjApiClient` 中。

### 2. TTL 24 小時 + stale-while-revalidate

**選擇**：快取 24 小時（86400 秒）。過期後若 API 呼叫失敗，fallback 到 stale cache。

```
get_tags_cached(source):
    cached = _tags_cache.get(source)   # (timestamp, tags)
    if cached and now - cached.ts < TTL:
        return cached.tags
    try:
        tags = await get_tags(source)
        _tags_cache[source] = (now, tags)
        return tags
    except:
        if cached:
            return cached.tags   # stale fallback
        return []                # no cache at all
```

**理由**：標籤變動頻率極低（數月才可能新增/刪除），24 小時 TTL 足夠保守。stale fallback 確保即使 API 暫時故障，autocomplete 仍能運作。

### 3. 透過 `interaction.namespace` 讀取當前 source

**選擇**：在 autocomplete callback 中讀取 `interaction.namespace.source` 來決定查詢哪個來源的標籤。預設值為 `"leetcode"`。

```python
@random_command.autocomplete("tags")
async def random_tags_autocomplete(self, interaction, current):
    source = (interaction.namespace.source if interaction.namespace else None) or "leetcode"
    tags = await self.bot.api.get_tags_cached(source)
    filtered = [t for t in tags if current.lower() in t.lower()]
    return [Choice(name=t, value=t) for t in filtered[:25]]
```

**替代方案**：為每個 source 預先建立靜態 choices list。

**理由**：靜態 choices 無法隨 source 變動（Discord 的 `@app_commands.choices` 是註冊時就固定的）。`interaction.namespace` 是 Discord.py 標準機制，讓 autocomplete 能回應使用者已選的其他參數。

### 4. Fire-and-forget 啟動預載入

**選擇**：在 `on_ready` 中對 `["leetcode", "codeforces"]` 發起 `asyncio.create_task(get_tags_cached())`，不等待結果。

**理由**：這兩個是最常用的來源，預載入可確保首次 autocomplete 無網路延遲。Fire-and-forget 不阻塞 bot 啟動。其他來源（atcoder、luogu、spoj）在使用者首次選用時 lazy load。

### 5. Autocomplete 失敗不回報錯誤給使用者

**選擇**：API 失敗時回傳空 `list[Choice]`，不顯示任何錯誤訊息。

**理由**：Autocomplete 是輔助功能，失敗時使用者仍可手動輸入 tags。顯示錯誤會造成不必要的干擾。

## Risks / Trade-offs

- **[快取不一致]** 若 upstream 新增/刪除標籤，使用者可能在 24 小時內看到過期的 autocomplete 建議 → 影響極低：標籤變更極罕見，且使用者仍可手動輸入新的標籤名稱
- **[記憶體]** 每個來源的快取約數十到數百個字串，所有來源總計 < 50KB → 可忽略
- **[Rate limit]** 預載入時同時發兩個 API request → OjApiClient 內建 `_inflight` dedup，不會重複請求同一端點
- **[冷啟動延遲]** 非熱門來源（如 spoj）在首次 autocomplete 時才發 API 請求，可能有 ~200ms 延遲 → 可接受，且此類來源使用頻率低
