import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from codeforces import CodeforcesClient
from utils.database import ProblemsDatabaseManager


@pytest.mark.asyncio
async def test_sync_problemset_parses_api(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    api_response = {
        "status": "OK",
        "result": {
            "problems": [
                {
                    "contestId": 2082,
                    "index": "A",
                    "name": "Foo",
                    "rating": 800,
                    "tags": ["math"],
                }
            ],
            "problemStatistics": [{"contestId": 2082, "index": "A", "solvedCount": 1000}],
        },
    }
    client._fetch_json = AsyncMock(return_value=api_response)

    problems = await client.sync_problemset()

    assert len(problems) == 1
    assert problems[0]["id"] == "2082A"


@pytest.mark.asyncio
async def test_problemset_api_error_returns_empty(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    client._fetch_json = AsyncMock(return_value={"status": "FAILED", "comment": "Call limit exceeded"})

    problems = await client.sync_problemset()

    assert problems == []


@pytest.mark.asyncio
async def test_fetch_contest_list_filters_finished(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    api_response = {
        "status": "OK",
        "result": [
            {"id": 2082, "phase": "FINISHED", "type": "CF"},
            {"id": 2083, "phase": "PENDING", "type": "CF"},
            {"id": 100001, "phase": "FINISHED", "type": "GYM"},
        ],
    }
    client._fetch_json = AsyncMock(return_value=api_response)

    contests = await client.fetch_contest_list(include_gym=False)

    assert contests == [2082]


@pytest.mark.asyncio
async def test_fetch_contest_list_handles_api_error(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    client._fetch_json = AsyncMock(
        return_value={
            "status": "FAILED",
            "comment": "contestId: Field should contain only digits",
        }
    )

    contests = await client.fetch_contest_list()

    assert contests == []


@pytest.mark.asyncio
async def test_fetch_contest_problems_parses_standings(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    api_response = {
        "status": "OK",
        "result": {
            "problems": [
                {
                    "contestId": 2082,
                    "index": "A",
                    "name": "Foo",
                    "rating": 800,
                    "tags": ["math"],
                },
                {
                    "contestId": 2082,
                    "index": "B",
                    "name": "Bar",
                    "rating": 1200,
                    "tags": [],
                },
            ]
        },
    }
    client._fetch_json = AsyncMock(return_value=api_response)

    problems = await client.fetch_contest_problems(2082, session=object())

    assert [problem["id"] for problem in problems] == ["2082A", "2082B"]
    assert problems[0]["rating"] == 800
    assert problems[1]["problem_index"] == "B"


@pytest.mark.asyncio
async def test_fetch_contest_problems_handles_api_error(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    client._fetch_json = AsyncMock(
        return_value={
            "status": "FAILED",
            "comment": "contestId: Contest with id 99999 not found",
        }
    )

    problems = await client.fetch_contest_problems(99999, session=object())

    assert problems == []


@pytest.mark.asyncio
async def test_fetch_problem_content_extracts_statement(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <div class="problem-statement">
      <img src="/predownloaded/test.png" />
      <a href="/contest/1234">Link</a>
    </div>
    """
    client._fetch_text = AsyncMock(return_value=html)

    content = await client.fetch_problem_content(session=object(), contest_id=2082, index="A")

    assert "https://codeforces.com/predownloaded/test.png" in content
    assert "https://codeforces.com/contest/1234" in content


def test_clean_problem_markdown_removes_header_and_overlay(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <div class="header">limits</div>
    <div class="ojb-overlay">cover</div>
    <div class="html2md-panel">panel</div>
    <div class="likeForm">like</div>
    <div class="monaco-editor">editor</div>
    <div class="overlay">cover</div>
    <div>ok</div>
    """
    cleaned = client._clean_problem_markdown(html)

    assert "limits" not in cleaned
    assert "panel" not in cleaned
    assert "editor" not in cleaned
    assert "ok" in cleaned


def test_clean_problem_markdown_converts_mathjax_and_normalizes_triple_dollar(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <span class="MathJax">rendered</span>
    <span class="MathJax_Preview">preview</span>
    <div class="MathJax_Display">rendered</div>
    <script type="math/tex">n \\leq 10^5</script>
    <script type="math/tex; mode=display">\\sum_{i=1}^{n}</script>
    <p>$$$a+b$$$</p>
    """
    cleaned = client._clean_problem_markdown(html)

    assert "$n \\leq 10^5$" in cleaned
    assert "$$" in cleaned
    assert "\\sum_{i=1}^{n}" in cleaned
    assert "$a+b$" in cleaned
    assert "$$$" not in cleaned
    assert "MathJax" not in cleaned


def test_clean_problem_markdown_converts_structure_blocks(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = """
    <div class="section-title">Input</div>
    <div class="property-title">Time limit</div>
    <div class="sample-tests">
      <div class="input"><pre>1 2</pre></div>
    </div>
    <pre>code line</pre>
    <table class="bordertable">
      <tr><th>A</th><th>B</th></tr>
      <tr><td>1</td><td>2</td></tr>
    </table>
    """
    cleaned = client._clean_problem_markdown(html)

    assert "## Input" in cleaned
    assert "**Time limit**:" in cleaned
    assert "```" in cleaned
    assert "1 2" in cleaned
    assert "code line" in cleaned
    assert "| A | B |" in cleaned


def test_fix_relative_urls(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '<img src="/predownloaded/test.png"><a href="/contest/1234">Link</a>'
    fixed = client._fix_relative_urls(html, "https://codeforces.com")

    assert "https://codeforces.com/predownloaded/test.png" in fixed
    assert "https://codeforces.com/contest/1234" in fixed


def test_fix_relative_urls_handles_protocol_relative(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = '<img src="//cdn.example.com/img.png">'
    fixed = client._fix_relative_urls(html, "https://codeforces.com")

    assert "https://cdn.example.com/img.png" in fixed


def test_is_rate_limited_detects_marker(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    html = "<title>Too many requests</title>"
    assert client._is_rate_limited(html) is True
    assert client._is_rate_limited("<a href='/enter'>login</a>") is True


def test_progress_file_roundtrip(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))

    client.save_progress(2082)
    progress = client.get_progress()

    assert "2082" in progress["fetched_contests"]


def test_progress_atomic_write(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))

    client.save_progress(2082)

    assert not (tmp_path / "codeforces_progress.tmp").exists()
    assert (tmp_path / "codeforces_progress.json").exists()


def test_tags_not_double_encoded(tmp_path):
    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    tags_json = json.dumps(["math", "dp"])

    assert client._serialize_tags(tags_json) == tags_json


def test_batch_insert_tags_roundtrip(tmp_path):
    db = ProblemsDatabaseManager(str(tmp_path / "db.sqlite"))
    problems = [
        {
            "id": "2082A",
            "source": "codeforces",
            "slug": "2082A",
            "title": "Test",
            "tags": json.dumps(["math", "dp"]),
        }
    ]
    db.update_problems(problems)

    problem = db.get_problem(id="2082A", source="codeforces")
    assert isinstance(problem["tags"], list)
    assert problem["tags"] == ["math", "dp"]


@pytest.mark.asyncio
async def test_reprocess_content_updates_changed_content(tmp_path):
    db = ProblemsDatabaseManager(str(tmp_path / "db.sqlite"))
    db.update_problem({"id": "1A", "source": "codeforces", "slug": "1A", "content": "<p>$$$x$$$</p>"})
    db.update_problem({"id": "2A", "source": "codeforces", "slug": "2A", "content": "<p>unchanged</p>"})

    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    updated = await client.reprocess_content()

    assert updated >= 1
    problem = db.get_problem(id="1A", source="codeforces")
    assert "$x$" in problem["content"]


@pytest.mark.asyncio
async def test_reprocess_content_skips_empty(tmp_path):
    db = ProblemsDatabaseManager(str(tmp_path / "db.sqlite"))
    db.update_problem({"id": "1A", "source": "codeforces", "slug": "1A", "content": ""})

    client = CodeforcesClient(data_dir=str(tmp_path), db_path=str(tmp_path / "db.sqlite"))
    updated = await client.reprocess_content()

    assert updated == 0
