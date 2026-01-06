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
