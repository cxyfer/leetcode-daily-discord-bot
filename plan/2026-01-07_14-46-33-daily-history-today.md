---
mode: plan
cwd: /mnt/d/Workspace/Github/leetcode-daily-discord-bot
task: 在 /daily Embed 中新增「歷史上的今天」Field
complexity: low
planning_method: builtin
created_at: 2026-01-07T15:10:29+08:00
updated_at: 2026-01-08T15:10:00+08:00
reviewed_by: [Claude, Gemini]
status: reviewed
---

# Plan: /daily Embed 新增 History Problems Field

## 🎯 任務概述

**目標**：在現有 `/daily`（及 `/daily_cn`）指令回傳的 Embed 中，於 `🔍 Similar Questions` 下方新增一個 `📅 History Problems` Field，顯示近五年相同月日的每日一題。

**核心原則**：
- ✅ 保留現有所有功能與行為
- ✅ 不新增任何指令參數
- ✅ 僅擴充 Embed 內容

**與原計畫差異**：
| 面向 | 原計畫 | 簡化版 |
|------|--------|--------|
| 行為變更 | 新增 `mode` 參數，預設改為 history | **保留原本行為** |
| UI 呈現 | 獨立的歷史 Embed + 按鈕列 | 在現有 Embed 中**新增一個 Field** |
| 複雜度 | 高（重構整個指令流程） | 低（僅擴充 Embed 內容）|

---

## 📊 目標 UI 呈現

```
現有 Embed 結構:
├── 🔗 題號. 題目標題
├── 🔥 Difficulty / ⭐ Rating / 📈 AC Rate
├── 🏷️ Tags
├── 🔍 Similar Questions
└── 📅 History Problems    ← 新增這一個 Field
    - [2025] 🟢 1408. String Matching in an Array *1234*
    - [2024] 🟡 2870. Minimum Number of Operations *1567*
    - [2023] 🔴 1531. String Compression II *2375*
    ...
```

**格式規範**：
- 每行格式：`- [{year}] {difficulty_emoji} {id}. {title} *{rating}*`
- 按年份降序排列（最新年份在前）
- 不顯示當天題目（避免重複）
- 若無歷史資料，不顯示此 Field

---

## 📋 執行計畫

### Step 1: 日期清單生成函數

**新增位置**: `leetcode.py`

```python
def generate_history_dates(anchor_date: str, years: int = 5) -> List[str]:
    """
    生成近 N 年同月同日的日期列表（不含當年）

    Args:
        anchor_date: 錨定日期，格式 YYYY-MM-DD
        years: 回溯年數，預設 5

    Returns:
        日期列表，降序排列 ["2025-01-07", "2024-01-07", ...]

    規則:
        - 跳過 2020-04-01 之前的日期（LeetCode Daily 起始日）
        - 跳過非閏年的 2/29
        - 不包含錨定日期當年
    """
```

**驗收標準**:
- [ ] 輸入 `2026-01-07` → 回傳 `["2025-01-07", "2024-01-07", "2023-01-07", "2022-01-07", "2021-01-07"]`
- [ ] 輸入 `2025-02-29`（閏年） → 回傳 `["2024-02-29", "2020-02-29"]`（僅閏年）
- [ ] 輸入 `2021-03-15` → 回傳 `["2020-04-01" 之後的有效日期]`
- [ ] 輸入 `2020-05-01` → 回傳空列表（無歷史）

---

### Step 2: 歷史資料批次獲取方法

**新增位置**: `leetcode.py` 內 `LeetCodeClient` class

```python
async def get_daily_history(
    self,
    anchor_date: str,
    years: int = 5
) -> List[Dict[str, Any]]:
    """
    批次獲取歷史同日每日挑戰

    Args:
        anchor_date: 錨定日期 YYYY-MM-DD
        years: 回溯年數

    Returns:
        challenges 列表，每筆包含:
        - date: str
        - id: int
        - title: str
        - difficulty: str
        - rating: int (optional)
        - link: str

    實作要點:
        - 使用 asyncio.gather 並發獲取
        - semaphore 限制最大 3 並發
        - 單次失敗不影響其他日期
        - 優先從本地 DB 讀取
        - 結果按日期降序排列
    """
```

**驗收標準**:
- [ ] 並發使用 `asyncio.Semaphore(3)` 限制
- [ ] 單一 API 失敗不中斷其他請求
- [ ] 回傳結果按日期降序排列
- [ ] 每筆包含必要欄位：date, id, title, difficulty, link, rating (optional)

---

### Step 3: Embed Field 生成

**修改位置**: `utils/ui_helpers.py` 的 `create_problem_embed()` 函數

**新增參數**:
```python
async def create_problem_embed(
    problem_info: Dict[str, Any],
    bot: Any,
    domain: str = "com",
    is_daily: bool = False,
    date_str: Optional[str] = None,
    user: Optional[discord.User] = None,
    title: Optional[str] = None,
    message: Optional[str] = None,
    history_problems: Optional[List[Dict[str, Any]]] = None,  # 新增
) -> discord.Embed:
```

**Field 生成邏輯**（插入於 Similar Questions 之後、Footer 之前）:
```python
# History problems field
if history_problems:
    history_lines = []
    for hp in history_problems[:5]:  # 最多顯示 5 筆
        year = hp["date"][:4]
        emoji = get_difficulty_emoji(hp["difficulty"])
        line = f"- [{year}] {emoji} [{hp['id']}. {hp['title']}]({hp['link']})"
        if hp.get("rating") and hp["rating"] > 0:
            line += f" *{int(hp['rating'])}*"
        history_lines.append(line)

    if history_lines:
        embed.add_field(
            name=f"{FIELD_EMOJIS['history']} History Problems",
            value="\n".join(history_lines),
            inline=False,
        )
```

**驗收標準**:
- [ ] Field 位於 Similar Questions 之後
- [ ] 格式符合規範：`- [{year}] {emoji} {id}. {title} *{rating}*`
- [ ] 無歷史資料時不顯示 Field
- [ ] 最多顯示 5 筆

---

### Step 4: 指令整合

**修改位置**: `cogs/slash_commands_cog.py` 及 `utils/ui_helpers.py`

**修改點 A** - `slash_commands_cog.py:59-109` 的 `daily_command`:
```python
# 在建立 embed 前獲取歷史資料
history_problems = await current_client.get_daily_history(date)

embed = await create_problem_embed(
    problem_info=challenge_info,
    bot=self.bot,
    domain="com",
    is_daily=True,
    date_str=date,
    history_problems=history_problems,  # 新增
)
```

**修改點 B** - `slash_commands_cog.py:111-160` 的 `daily_cn_command`:
同上邏輯

**修改點 C** - `ui_helpers.py:531-600` 的 `send_daily_challenge`:
```python
# 在建立 embed 前獲取歷史資料
history_problems = await current_client.get_daily_history(date_str)

embed = await create_problem_embed(
    problem_info=challenge_info,
    bot=bot,
    domain=domain,
    is_daily=True,
    date_str=date_str,
    history_problems=history_problems,  # 新增
)
```

**驗收標準**:
- [ ] `/daily` 指令正常顯示歷史題目
- [ ] `/daily_cn` 指令正常顯示歷史題目
- [ ] 排程推播正常顯示歷史題目
- [ ] 指定日期查詢正常顯示歷史題目

---

### Step 5: 常數與 Emoji 定義

**修改位置**: `utils/ui_constants.py`

**新增**:
```python
FIELD_EMOJIS = {
    # ... existing
    "history": "📅",  # 新增
}
```

---

## 📎 參考檔案

| 檔案 | 行號 | 說明 |
|------|------|------|
| `cogs/slash_commands_cog.py` | 54-109 | /daily 指令 |
| `cogs/slash_commands_cog.py` | 111-160 | /daily_cn 指令 |
| `leetcode.py` | 564-641 | get_daily_challenge 方法 |
| `leetcode.py` | 791-884 | fetch_monthly_daily_challenges 方法 |
| `utils/ui_helpers.py` | 73-208 | create_problem_embed 函數 |
| `utils/ui_helpers.py` | 531-600 | send_daily_challenge 函數 |
| `utils/ui_constants.py` | 35-47 | FIELD_EMOJIS 定義 |
| `utils/database.py` | 1033-1067 | get_daily_by_date 方法 |

---

## ⚠️ 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| API 速率限制 | 請求被拒絕 | semaphore(3) + 優先讀取本地 DB |
| Discord 3 秒回應限制 | interaction 失敗 | 已使用 `defer()` |
| Embed 欄位超限 | 顯示失敗 | 限制最多 5 筆歷史 |
| CN 域歷史資料不足 | 功能受限 | 僅顯示有資料的年份 |

---

## 📊 審查紀錄

**更新日期**: 2026-01-08
**狀態**: ✅ 審查完成

### Gemini 審查結果

**審查時間**: 2026-01-08 03:06 UTC
**模型**: auto-gemini-3
**結論**: 計畫設計合理，提供了完整的 Unified Diff Patch

**主要確認事項**:
1. ✅ `generate_history_dates` 邊界條件處理完善
   - 使用 `datetime.strptime` 驗證日期格式
   - 使用 `dt.replace(year=...)` 配合 `try/except ValueError` 處理閏年
   - 正確設定最早日期為 `2020-04-01`
2. ✅ 並發獲取的錯誤處理策略正確
   - 使用 `asyncio.Semaphore(3)` 限制並發
   - 使用 `try/except` 記錄錯誤但不中斷其他請求
   - 過濾 `None` 結果後返回
3. ✅ Field 位置與格式設計正確
   - 位於 Similar Questions 之後、Footer 之前
   - 格式符合規範

### Codex 審查結果

**狀態**: ⚠️ 連接超時，未能完成審查

---

## 📝 實作參考

### Gemini 提供的 Unified Diff Patch

以下為 Gemini 提供的參考實作，作為實際編碼時的基準：

<details>
<summary>展開查看完整 Diff</summary>

```diff
--- leetcode.py
+++ leetcode.py
@@ -17,6 +17,29 @@
 logger = get_leetcode_logger()


+def generate_history_dates(anchor_date: str, years: int = 5) -> list[str]:
+    """
+    Generate a list of dates for the same day in previous years.
+    Skips dates before 2020-04-01 (LeetCode Daily Challenge start).
+    Skips Feb 29 on non-leap years.
+    """
+    try:
+        dt = datetime.strptime(anchor_date, "%Y-%m-%d")
+    except ValueError:
+        return []
+
+    dates = []
+    min_date = datetime(2020, 4, 1)
+
+    for i in range(1, years + 1):
+        try:
+            target_date = dt.replace(year=dt.year - i)
+            if target_date >= min_date:
+                dates.append(target_date.strftime("%Y-%m-%d"))
+        except ValueError:
+            continue
+    return dates
+
 class LeetCodeClient:
@@ -536,6 +559,23 @@

                 return daily

+    async def get_daily_history(self, anchor_date: str, years: int = 5) -> list[dict]:
+        """
+        Fetch daily challenges for the same day in previous years.
+        """
+        dates = generate_history_dates(anchor_date, years)
+        if not dates:
+            return []
+
+        sem = asyncio.Semaphore(3)
+
+        async def fetch(date):
+            async with sem:
+                try:
+                    return await self.get_daily_challenge(date_str=date, domain=self.domain)
+                except Exception as e:
+                    logger.warning(f"Failed to fetch history for {date}: {e}")
+                    return None
+
+        results = await asyncio.gather(*[fetch(d) for d in dates])
+        return [r for r in results if r]
+
--- utils/ui_constants.py
+++ utils/ui_constants.py
@@ -42,6 +42,7 @@
     "instructions": "💡",
     "problems": "📋",
     "link": "🔗",
+    "history": "📅",
 }

--- utils/ui_helpers.py
+++ utils/ui_helpers.py
@@ -69,6 +69,7 @@
     user: Optional[discord.User] = None,
     title: Optional[str] = None,
     message: Optional[str] = None,
+    history_problems: Optional[List[Dict[str, Any]]] = None,
 ) -> discord.Embed:
@@ -155,6 +156,20 @@
                 inline=False,
             )

+    # History problems field
+    if history_problems:
+        history_lines = []
+        for hp in history_problems[:5]:  # Show max 5 entries
+            year = hp["date"][:4]
+            emoji = get_difficulty_emoji(hp["difficulty"])
+            line = f"- [{year}] {emoji} [{hp['id']}. {hp['title']}]({hp['link']})"
+            if hp.get("rating") and hp["rating"] > 0:
+                line += f" *{int(hp['rating'])}*"
+            history_lines.append(line)
+
+        if history_lines:
+            embed.add_field(
+                name=f"{FIELD_EMOJIS['history']} History Problems",
+                value="\n".join(history_lines),
+                inline=False,
+            )
+
     # Set footer
@@ -536,6 +551,8 @@
         challenge_info = await current_client.get_daily_challenge()

+        history_problems = await current_client.get_daily_history(challenge_info["date"])
+
         embed = await create_problem_embed(
             problem_info=challenge_info,
             bot=bot,
             domain=domain,
             is_daily=True,
+            history_problems=history_problems,
         )

--- cogs/slash_commands_cog.py
+++ cogs/slash_commands_cog.py
@@ -62,6 +62,8 @@
                     return

+                history_problems = await current_client.get_daily_history(date)
+
                 embed = await create_problem_embed(
                     problem_info=challenge_info,
                     bot=self.bot,
                     domain="com",
                     is_daily=True,
                     date_str=date,
+                    history_problems=history_problems,
                 )
@@ -101,6 +103,8 @@
                     return

+                history_problems = await current_client.get_daily_history(date)
+
                 embed = await create_problem_embed(
                     problem_info=challenge_info,
                     bot=self.bot,
                     domain="cn",
                     is_daily=True,
                     date_str=date,
+                    history_problems=history_problems,
                 )
```

</details>
