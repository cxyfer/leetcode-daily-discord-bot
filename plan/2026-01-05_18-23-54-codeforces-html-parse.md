---
mode: plan
cwd: /mnt/d/Workspace/Github/leetcode-daily-discord-bot
task: Codeforces 題目敘述 HTML 解析優化（參考 OJBetter）
complexity: medium
planning_method: builtin
created_at: 2026-01-05T18:24:35.845797+08:00
updated_at: 2026-01-05T21:30:00+08:00
---

# Plan: Codeforces 題目敘述 HTML 解析優化

## 🎯 任務概述

目前 Codeforces 題目敘述直接以 raw HTML 儲存，導致後續顯示仍充滿標籤。目標是參考 OJBetter 的 turndown 清理規則，將題目敘述轉為更乾淨的 Markdown/純文字，同時保留範例輸入輸出等核心資訊。

---

## 🔧 設計決策

| 項目 | 決策 | 說明 |
|------|------|------|
| `.header` 區塊 | **完全移除** | time/memory limit 等資訊已在 embed 中顯示 |
| `.sample-tests` 區塊 | **保留並格式化** | 轉換為 Markdown code block |
| 數學公式 | **分層處理** | 儲存層保留 `$...$` 格式，輸出層轉為純文字 |

### 數學公式處理架構

```
Codeforces HTML (MathJax)
        ↓
_clean_problem_html() [codeforces.py]
        ↓ 轉換為 $latex$ 格式
Database (content field)
        ↓
html_to_text() [leetcode.py]
        ↓ 將 $...$ 轉為純文字
LLM Translation / Discord Display
```

---

## 📊 現況分析

### 資料流程

```
Codeforces HTML Page
        ↓
_extract_problem_statement() [codeforces.py:278]
        ↓ (raw HTML with relative URLs fixed)
Database (content field)
        ↓
html_to_text() [leetcode.py:1015]
        ↓ (Markdown/text)
LLM Translation / Discord Display
```

### 現有實作

| 檔案 | 行號 | 功能 |
|------|------|------|
| `codeforces.py` | 278-283 | `_extract_problem_statement()`: 提取 `div.problem-statement`，僅修正相對 URL |
| `leetcode.py` | 1015-1131 | `html_to_text()`: 通用 HTML→Markdown 轉換，支援 AtCoder/LeetCode |
| `interaction_handler_cog.py` | 202, 295, 480 | 呼叫 `html_to_text()` 進行翻譯前處理 |

### 本專案清理規則

**移除的元素：**
- `.header`（time/memory limit 等，已在 embed 顯示）
- `.ojb-overlay`, `.html2md-panel`, `.likeForm`, `.monaco-editor`
- `script`（MathJax script 除外，需先提取）, `style`

**保留並格式化的元素：**
- `.sample-tests`（轉為 Markdown code block）
- `del` 標籤

**轉換規則：**
| HTML 元素 | 轉換結果 |
|-----------|----------|
| `script[type^=math/tex]` | `$latex$`（儲存層保留） |
| `span.tex-font-style-bf` | `**bold**` |
| `div.section-title` | `## title` |
| `div.property-title` | `**title**: ` |
| `pre` | ` ```code``` ` |
| `table.bordertable` | Markdown table |

---

## 📋 執行計畫

### Phase 1: 新增 Codeforces 專用清理函式

**目標**：在 `codeforces.py` 中新增 `_clean_problem_html()` 方法

**前置條件**：在 `codeforces.py` 頂部新增 `import re`

**步驟**：

1.1. 在 `CodeforcesClient` 類別中新增 `_clean_problem_html(self, html: str) -> str` 方法

1.2. 實作以下清理邏輯（**注意：MathJax 必須在移除 script 之前處理**）：
```python
def _clean_problem_html(self, html: str) -> str:
    """Clean Codeforces problem HTML before conversion."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")

    # ⚠️ 關鍵：先處理 MathJax（在移除 script 之前！）
    # 以 script[type^=math/tex] 為主體處理，避免 sibling 查找問題
    for script in soup.select("script[type^='math/tex']"):
        latex = script.get_text()
        is_display = "mode=display" in script.get("type", "")
        # 移除相鄰的 MathJax 渲染容器
        prev = script.find_previous_sibling()
        if prev and any(c.startswith("MathJax") for c in prev.get("class", [])):
            prev.decompose()
        # 保留 LaTeX 格式（輸出層再轉換）
        if is_display:
            script.replace_with(f"\n$$\n{latex}\n$$\n")
        else:
            script.replace_with(f"${latex}$")

    # 清理剩餘的 MathJax 容器（無對應 script 的情況）
    for el in soup.select("span.MathJax, span.MathJax_Preview, div.MathJax_Display"):
        el.decompose()

    # 移除不需要的元素（現在可以安全移除 script）
    for selector in [".header", "script", "style", ".ojb-overlay"]:
        for el in soup.select(selector):
            el.decompose()

    # 轉換 Codeforces 特有元素
    for el in soup.select("span.tex-font-style-bf"):
        el.replace_with(f"**{el.get_text()}**")

    for el in soup.select("div.section-title"):
        el.replace_with(f"\n## {el.get_text().strip()}\n")

    for el in soup.select("div.property-title"):
        el.replace_with(f"**{el.get_text().strip()}**: ")

    # 處理 table.bordertable
    for table in soup.select("table.bordertable"):
        rows = table.find_all("tr")
        if not rows:
            continue
        md_rows = []
        for i, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            md_row = "| " + " | ".join(c.get_text(strip=True) for c in cells) + " |"
            md_rows.append(md_row)
            if i == 0:
                md_rows.append("| " + " | ".join("---" for _ in cells) + " |")
        table.replace_with("\n" + "\n".join(md_rows) + "\n")

    return str(soup)
```

1.3. 修改 `_extract_problem_statement()` 呼叫清理函式：
```python
def _extract_problem_statement(self, html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    statement = soup.select_one("div.problem-statement")
    if not statement:
        return None
    cleaned = self._clean_problem_html(str(statement))
    return self._fix_relative_urls(cleaned, "https://codeforces.com")
```

**驗收標準**：
- [ ] `_clean_problem_html()` 方法存在且可正常執行
- [ ] MathJax 元素被正確轉換為 `$...$` 或 `$$...$$` 格式
- [ ] `.header` 等無用元素被移除
- [ ] `section-title` 轉換為 Markdown 標題
- [ ] `table.bordertable` 轉換為 Markdown table

---

### Phase 2: 強化 html_to_text() 的 LaTeX 轉換

**目標**：在輸出層將 `$...$` 格式的 LaTeX 轉換為純文字

**步驟**：

2.1. 在 `leetcode.py` 的 `html_to_text()` 中新增 LaTeX 轉換函式：

```python
def _latex_to_plain(latex: str) -> str:
    """Convert LaTeX math notation to plain text."""
    replacements = [
        (r"\leq", "<="), (r"\geq", ">="), (r"\neq", "!="),
        (r"\le", "<="), (r"\ge", ">="), (r"\ne", "!="),
        (r"\times", "*"), (r"\cdot", "*"), (r"\div", "/"),
        (r"\pm", "+-"), (r"\infty", "inf"),
        (r"\ldots", "..."), (r"\cdots", "..."),
        (r"\lvert", "|"), (r"\rvert", "|"),
        (r"\lfloor", "floor("), (r"\rfloor", ")"),
        (r"\lceil", "ceil("), (r"\rceil", ")"),
    ]
    result = latex
    for old, new in replacements:
        result = result.replace(old, new)
    result = re.sub(r"\\(?:mathrm|text|mathbf|mathit)\s*", "", result)
    result = re.sub(r"\s*\^\s*", "^", result)
    result = re.sub(r"\s*_\s*", "_", result)
    return result.strip()
```

2.2. 在 `html_to_text()` 中處理 `$...$` 和 `$$...$$`：

```python
# 在 replace_latex_tokens() 之後新增
# 處理 Codeforces 的 $...$ 格式
def convert_latex_delimiters(text: str) -> str:
    # 處理 display math $$...$$
    text = re.sub(
        r'\$\$\s*(.+?)\s*\$\$',
        lambda m: _latex_to_plain(m.group(1)),
        text,
        flags=re.DOTALL
    )
    # 處理 inline math $...$
    text = re.sub(
        r'\$(.+?)\$',
        lambda m: _latex_to_plain(m.group(1)),
        text
    )
    return text

text = convert_latex_delimiters(text)
```

**驗收標準**：
- [ ] `$n \leq 10^5$` 轉換為 `n <= 10^5`
- [ ] `$$\sum_{i=1}^{n}$$` 轉換為 `sum_i=1^n`
- [ ] AtCoder/LeetCode 現有功能不受影響

---

### Phase 3: 測試案例擴充

**目標**：新增 Codeforces 專用測試案例，覆蓋所有邊界情況

**步驟**：

3.1. 在 `tests/test_codeforces.py` 新增測試：

```python
def test_clean_problem_html_removes_header(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '''
    <div class="problem-statement">
      <div class="header">
        <div class="title">A. Problem Name</div>
        <div class="time-limit">time limit per test: 1 second</div>
      </div>
      <div>Problem content here</div>
    </div>
    '''
    cleaned = client._clean_problem_html(html)
    assert "class=\"header\"" not in cleaned
    assert "Problem content here" in cleaned


def test_clean_problem_html_converts_mathjax_to_latex(tmp_path):
    """測試 MathJax 轉換為 $latex$ 格式（儲存層）"""
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '''
    <span class="MathJax">rendered</span>
    <script type="math/tex">n \\leq 10^5</script>
    '''
    cleaned = client._clean_problem_html(html)
    assert "$n \\leq 10^5$" in cleaned
    assert "MathJax" not in cleaned


def test_clean_problem_html_display_math(tmp_path):
    """測試 display math 轉換為 $$...$$ 格式"""
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '''
    <div class="MathJax_Display">rendered</div>
    <script type="math/tex; mode=display">\\sum_{i=1}^{n}</script>
    '''
    cleaned = client._clean_problem_html(html)
    assert "$$" in cleaned
    assert "\\sum_{i=1}^{n}" in cleaned


def test_clean_problem_html_mathjax_missing_script(tmp_path):
    """測試缺少 script 的 MathJax span"""
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '<span class="MathJax">orphan</span>'
    cleaned = client._clean_problem_html(html)
    assert "MathJax" not in cleaned


def test_clean_problem_html_converts_section_title(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '<div class="section-title">Input</div>'
    cleaned = client._clean_problem_html(html)
    assert "## Input" in cleaned


def test_clean_problem_html_converts_table(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '<table class="bordertable"><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>'
    cleaned = client._clean_problem_html(html)
    assert "| A | B |" in cleaned
    assert "| --- | --- |" in cleaned
    assert "| 1 | 2 |" in cleaned
```

3.2. 在 `tests/test_html_to_text.py` 新增 LaTeX 轉換測試：

```python
def test_html_to_text_latex_to_plain():
    """測試 $...$ 格式轉換為純文字（輸出層）"""
    html = '<p>Given $n \\leq 10^5$ elements.</p>'
    output = html_to_text(html)
    assert "n <= 10^5" in output
    assert "$" not in output


def test_html_to_text_display_math():
    """測試 $$...$$ 格式轉換"""
    html = '<p>Formula: $$a \\times b$$</p>'
    output = html_to_text(html)
    assert "a * b" in output
    assert "$$" not in output
```

**驗收標準**：
- [ ] 所有新增測試通過
- [ ] 現有測試不受影響（`pytest tests/` 全部通過）

---

### Phase 4: 資料遷移與 CLI 支援

**目標**：提供重新處理現有資料的方式

**步驟**：

4.1. 新增 CLI 選項 `--reprocess-content`：
```python
parser.add_argument(
    "--reprocess-content",
    action="store_true",
    help="Reprocess all Codeforces problem content with new cleaning rules",
)
```

4.2. 實作重新處理邏輯：
```python
async def reprocess_all_content(self) -> int:
    """Reprocess all stored problem content with updated cleaning rules."""
    problems = self.problems_db.get_all_problems(source="codeforces")
    updated = 0
    for problem in problems:
        if not problem.get("content"):
            continue
        # Re-clean the HTML content
        cleaned = self._clean_problem_html(problem["content"])
        if cleaned != problem["content"]:
            self.problems_db.update_problem({
                "id": problem["id"],
                "source": "codeforces",
                "content": cleaned
            })
            updated += 1
    return updated
```

**驗收標準**：
- [ ] `--reprocess-content` 選項可正常執行
- [ ] 重新處理後的內容格式正確

---

### Phase 5: 回歸驗證

**目標**：確保變更不影響現有功能

**步驟**：

5.1. 執行完整測試套件：
```bash
uv run pytest tests/ -v
```

5.2. 手動驗證 Discord Bot 功能：
- 使用 `/cf` 指令取得 Codeforces 題目
- 點擊「翻譯」按鈕確認翻譯結果格式正確
- 確認 AtCoder/LeetCode 題目翻譯不受影響

5.3. 檢查 LLM 翻譯品質：
- 清理後的文字應更易於 LLM 理解
- 數學公式應保持完整

**驗收標準**：
- [ ] `pytest tests/` 全部通過
- [ ] Discord Bot 翻譯功能正常
- [ ] AtCoder/LeetCode 功能不受影響

---

## ⚠️ 風險與緩解措施

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 清理過度導致內容遺失 | 題目關鍵資訊被刪除 | 明確定義保留清單，充分測試 |
| MathJax 解析失敗 | 數學公式顯示異常 | 保留原始 HTML 作為 fallback |
| 破壞現有翻譯流程 | AtCoder/LeetCode 翻譯異常 | 獨立的 Codeforces 清理函式，不修改通用邏輯 |
| 資料庫格式不相容 | 舊資料無法正常顯示 | 提供 `--reprocess-content` 遷移工具 |

---

## 📎 參考資料

### 程式碼位置
- `codeforces.py:278-283` - `_extract_problem_statement()`
- `codeforces.py:267-276` - `_fix_relative_urls()`
- `leetcode.py:1015-1131` - `html_to_text()`
- `tests/test_codeforces.py:131-145` - 現有 Codeforces 測試
- `tests/test_html_to_text.py:9-51` - 現有 HTML 轉換測試
- `cogs/interaction_handler_cog.py:202,295,480` - 翻譯呼叫點

### 外部參考
- [OJBetter Codeforces Script](https://github.com/beijixiaohu/OJBetter/blob/main/script/release/codeforces-better.user.js)
- [Turndown.js](https://github.com/mixmark-io/turndown)

---

## ✅ 總體驗收標準

1. **功能完整性**
   - [ ] Codeforces 題目 HTML 被正確清理為 Markdown
   - [ ] MathJax 數學公式在儲存層轉換為 `$...$` 格式
   - [ ] MathJax 數學公式在輸出層轉換為純文字
   - [ ] `section-title`, `property-title` 等元素正確轉換
   - [ ] 無用元素（header, script, style）被移除

2. **相容性**
   - [ ] AtCoder 題目翻譯功能正常
   - [ ] LeetCode 題目翻譯功能正常
   - [ ] 現有測試全部通過

3. **可維護性**
   - [ ] 新增測試覆蓋所有轉換規則
   - [ ] 提供資料遷移工具
   - [ ] 程式碼符合現有風格

4. **效能**
   - [ ] 清理過程不顯著增加處理時間
   - [ ] 不增加額外的網路請求
