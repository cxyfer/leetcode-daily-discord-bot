import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from atcoder import AtCoderClient


@pytest.mark.asyncio
async def test_fetch_contest_list_parses_archive(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <html><body>
      <a href="/contests/abc001">abc001</a>
      <a href="/contests/abc002">abc002</a>
    </body></html>
    """
    client._fetch_text = AsyncMock(return_value=html)

    contests = await client.fetch_contest_list(pages=1)

    assert contests == ["abc001", "abc002"]


@pytest.mark.asyncio
async def test_fetch_contest_problems_parses_tasks(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <table>
      <tbody>
        <tr>
          <td>A</td>
          <td><a href="/contests/abc001/tasks/abc001_a">A - Foo</a></td>
        </tr>
        <tr>
          <td>B</td>
          <td><a href="/contests/abc001/tasks/abc001_b">B - Bar</a></td>
        </tr>
      </tbody>
    </table>
    """
    client._fetch_text = AsyncMock(return_value=html)

    problems = await client.fetch_contest_problems("abc001", session=object())

    assert [p["id"] for p in problems] == ["abc001_a", "abc001_b"]
    assert problems[0]["problem_index"] == "A"
    assert problems[0]["title"] == "Foo"


@pytest.mark.asyncio
async def test_fetch_problem_content_prefers_english(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <div id="task-statement">
      <span class="lang-en">English</span>
    </div>
    """
    client._fetch_text = AsyncMock(return_value=html)

    content = await client.fetch_problem_content(session=object(), contest_id="abc001", problem_id="abc001_a")

    assert "English" in content
    assert "lang-en" not in content


@pytest.mark.asyncio
async def test_fetch_problem_content_fallbacks_to_japanese(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html_en = '<div id="task-statement"></div>'
    html_ja = '<span class="lang-ja">Japanese</span>'
    client._fetch_text = AsyncMock(side_effect=[html_en, html_ja])

    content = await client.fetch_problem_content(session=object(), contest_id="abc001", problem_id="abc001_a")

    assert "Japanese" in content
    assert "lang-ja" not in content


def test_clean_problem_markdown_converts_structure(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <span class="lang-en">
    <p>Score : <var>500</var> points</p>
    <div class="part">
    <section>
    <h3>Problem Statement</h3><p>Given are positive integers <var>a, b</var>.</p>
    </section>
    </div>
    <div class="part">
    <section>
    <h3>Constraints</h3><ul>
    <li><var>1\\leq a, b&lt; 10^{100000}</var></li>
    </ul>
    </section>
    </div>
    <hr/>
    <div class="io-style">
    <div class="part">
    <section>
    <h3>Input</h3><pre><var>a</var>\n<var>b</var>\n</pre>
    </section>
    </div>
    <div class="part">
    <section>
    <h3>Output</h3><p>Print <var>a</var> then <var>b</var>.</p>
    </section>
    </div>
    </div>
    <p><a href="/contests/abc001">Link</a></p>
    <p><img src="/img.png" alt="diagram" /></p>
    </span>
    """

    cleaned = client._clean_problem_markdown(html)
    normalized = " ".join(cleaned.split())

    assert "Score : $500$ points" in normalized
    assert "Score :\n$500$" not in cleaned
    assert "$500$\n points" not in cleaned
    assert "## Problem Statement" in cleaned
    assert "Given are positive integers $a, b$." in normalized
    assert "## Constraints" in cleaned
    assert "- $1\\leq a, b< 10^{100000}$" in normalized
    assert "-\n$1\\leq a, b< 10^{100000}$" not in cleaned
    assert "## Input" in cleaned
    assert "## Output" in cleaned
    assert "```" in cleaned
    assert "a" in cleaned
    assert "b" in cleaned
    assert "[Link](https://atcoder.jp/contests/abc001)" in cleaned
    assert "![diagram](https://atcoder.jp/img.png)" in cleaned
    assert "<span" not in cleaned


def test_progress_file_roundtrip(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))

    client.save_progress("abc123")
    progress = client.get_progress()

    assert "abc123" in progress["fetched_contests"]


def test_headers_include_accept_language_and_referer(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))

    headers = client._headers("https://example.com/contests/abc001")

    assert headers["User-Agent"] == "LeetCodeDailyDiscordBot/1.0"
    assert headers["Accept"].startswith("text/html")
    assert "Accept-Language" in headers
    assert headers["Referer"] == "https://example.com/contests/abc001"


def test_permission_denied_ignores_nav_sign_in(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = "<nav>Sign In</nav><div id='task-statement'>OK</div>"

    assert client._is_permission_denied(html) is False


def test_permission_denied_detects_explicit_denial(tmp_path):
    client = AtCoderClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = "<title>Permission Denied</title>"

    assert client._is_permission_denied(html) is True
