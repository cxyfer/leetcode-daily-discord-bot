## Why

`/similar` 目前只會回傳相似題目清單，使用者若想查看單一題目的完整資訊，必須再手動執行 `/problem` 或點外部連結，和 `/problem` 多題模式已提供的詳情按鈕體驗不一致。這個變更要讓 `/similar` 與題目卡片中的相似題目回覆都能直接開啟單題詳情，同時明確受 Discord 按鈕上限保護，避免在結果數過多時產生超限元件。

## What Changes

- 讓 slash `/similar` 的多結果回覆在安全按鈕數量範圍內附帶每題詳情按鈕，可直接開啟既有單題 problem card。
- 讓從單題卡片點擊「相似題目」後產生的相似題目回覆，也在相同限制下提供一致的詳情按鈕體驗。
- 將相似題目詳情入口對齊既有 `problem|{source}|{problem_id}|view` 互動協議，避免引入新的按鈕路由格式。
- 明確定義相似題目回覆何時可以顯示詳情按鈕：只有在結果數不超過目前可安全依賴的 Discord/discord.py View 按鈕上限時才顯示；超過時維持純結果清單回覆。
- 明確保留現有 `/similar` 的遠端 API-only 架構，不新增本地相似度索引或額外資料來源。

## Capabilities

### New Capabilities
- `similar-result-details`: 為 `/similar` 相關結果提供可直接開啟單題詳情的互動入口，並定義按鈕顯示的安全退化規則。

### Modified Capabilities
- `discord-ui`: 調整相似題目結果訊息的 UI 行為，使其在符合 Discord 元件限制時可附帶詳情按鈕，並在超限時安全退化。
- `interaction-handler`: 既有 problem view 互動路由需涵蓋從相似題目結果發出的詳情按鈕，維持持久化按鈕協議與單題卡片開啟流程。
- `embedding-search`: `/similar` 的結果呈現需求將從純 embed 清單擴充為「清單 + 條件式詳情入口」，且兩條 `/similar` 使用路徑都必須維持 remote API-only 契約。

## Impact

- Affected code: `src/bot/cogs/similar_cog.py`, `src/bot/cogs/interaction_handler_cog.py`, `src/bot/utils/ui_helpers.py`, `src/bot/utils/ui_constants.py`, `src/bot/utils/config.py`
- Affected runtime behavior: slash `/similar` 回覆、單題卡片中的「相似題目」互動回覆、既有 problem detail button flow
- Affected constraints: `top_k` 預設值維持 5；現有 slash `/similar` 上限為 20；按鈕顯示需遵守目前專案可安全依賴的 5 rows × 5 buttons 規則
- External dependencies: Discord message component limits、discord.py `View` / `ActionRow` 約束、遠端 similarity API 回傳的 `source` / `id` 資料契約
