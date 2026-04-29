# Proposal: /random 指令

## 概述

新增 `/random` 斜線指令，讓使用者可以隨機取得 LeetCode 題目，並支援難度、標籤、評分範圍篩選。

## 動機

使用者在日常練習時，除了每日挑戰外，也需要一個快速取得隨機題目的方式。`/random` 可以搭配篩選條件，幫助使用者針對特定難度或主題進行練習。

## 技術發現

### 後端 API 已支援

OJ API (`GET /api/v1/problems/{source}`) 已支援以下篩選與分頁參數：
- `difficulty`: Easy / Medium / Hard
- `tags`: 標籤篩選
- `rating_min` / `rating_max`: 評分範圍
- `per_page` + 頁碼分頁

實作策略：兩次 API 呼叫 — 第一次取總數 → 隨機選頁 → 第二次取題目。

### 現有架構可複用

| 模組 | 複用方式 |
|------|---------|
| `create_problem_embed` | 產生題目 Embed（含難度顏色） |
| `create_problem_view` | 產生互動按鈕（描述/翻譯/靈感/相似） |
| `InteractionHandlerCog` | 已有 `problem\|{source}\|{id}\|{action}` 統一路由 |
| 錯誤處理模式 | 沿用 `ApiProcessingError` / `ApiNetworkError` / `ApiRateLimitError` 標準映射 |

### 無需新增本地快取

資料庫目前不存儲可搜尋的題目目錄，但後端 API 已提供完整篩選能力，無需引入本地快取架構。

## 使用者確認

- **題庫來源**：僅 LeetCode（第一版）
- **Rating 篩選**：支援 `rating_min` / `rating_max`
- **預設行為**：無篩選條件時，從全題庫隨機

## 範圍

### 包含

- `/random` 斜線指令，支援以下參數：
  - `difficulty`: 難度篩選 (Easy/Medium/Hard)
  - `tags`: 標籤篩選
  - `rating_min`: 最低評分
  - `rating_max`: 最高評分
  - `public`: 是否公開顯示（沿用現有慣例）
- `OjApiClient` 新增 `get_random_problem()` 方法
- 沿用現有 UI 組件（Embed + View + 按鈕互動）
- `config.toml.example` 更新文件

### 不包含

- 多來源支援（AtCoder、Codeforces 等）— 留待後續版本
- 本地題目快取/索引
- 標籤自動完成（需額外 API 支援）
- 使用者歷史排除（避免重複推薦）

## 驗收標準

1. `/random` 回傳一個有效的 LeetCode 題目 Embed
2. `/random difficulty:Medium` 只回傳 Medium 難度題目
3. `/random tags:Array` 只回傳包含 Array 標籤的題目
4. `/random rating_min:1500 rating_max:2000` 只回傳評分在範圍內的題目
5. 無符合條件時，顯示明確的錯誤訊息
6. 回傳的題目包含所有標準互動按鈕（描述/翻譯/靈感/相似）
7. 錯誤處理與其他指令一致（Processing/Network/RateLimit/API）
