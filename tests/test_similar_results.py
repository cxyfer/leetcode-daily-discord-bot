import discord
import pytest

from bot.utils.ui_helpers import create_similar_results_message


def _make_similar_item(problem_id: str, *, source: str = "leetcode", difficulty: str = "Easy") -> dict:
    separator = ". " if source == "leetcode" else ": "
    return {
        "id": problem_id,
        "source": source,
        "title": f"{source}{separator}{problem_id}",
        "difficulty": difficulty,
        "similarity": 0.91,
        "link": f"https://example.com/{source}/{problem_id}",
    }


def _make_similar_payload(results: list[dict]) -> dict:
    return {"results": results}


@pytest.mark.asyncio
async def test_create_similar_results_message_attaches_detail_buttons_for_safe_results():
    payload = _make_similar_payload(
        [
            _make_similar_item("1"),
            _make_similar_item("2"),
            _make_similar_item("3", source="atcoder", difficulty=""),
            _make_similar_item("4"),
            _make_similar_item("5"),
            _make_similar_item("6", source="luogu", difficulty="入门"),
        ]
    )

    embed, view = create_similar_results_message(payload, base_source="leetcode", base_id="100")

    assert isinstance(embed, discord.Embed)
    assert view is not None
    assert [item.label for item in view.children] == ["1", "2", "3", "4", "5", "6"]
    assert [item.custom_id for item in view.children] == [
        "problem|leetcode|1|view",
        "problem|leetcode|2|view",
        "problem|atcoder|3|view",
        "problem|leetcode|4|view",
        "problem|leetcode|5|view",
        "problem|luogu|6|view",
    ]
    assert [item.row for item in view.children] == [0, 0, 0, 0, 0, 1]
    assert [str(item.emoji) for item in view.children] == ["🟢", "🟢", "🧩", "🟢", "🟢", "🔴"]


def test_create_similar_results_message_fails_closed_for_invalid_routing_fields():
    payload = _make_similar_payload(
        [
            _make_similar_item("1"),
            _make_similar_item("bad|id"),
        ]
    )

    _, view = create_similar_results_message(payload)

    assert view is None


def test_create_similar_results_message_fails_closed_for_overflow_results():
    payload = _make_similar_payload([_make_similar_item(str(i)) for i in range(1, 27)])

    _, view = create_similar_results_message(payload)

    assert view is None


def test_create_similar_results_message_handles_missing_routing_fields_without_crashing():
    payload = _make_similar_payload(
        [
            {
                "title": "Missing source",
                "difficulty": "Easy",
                "similarity": 0.91,
                "link": "https://example.com/missing-source",
            },
            _make_similar_item("2"),
        ]
    )

    embed, view = create_similar_results_message(payload)

    assert isinstance(embed, discord.Embed)
    assert view is None


def test_create_similar_results_message_fails_closed_for_overlong_button_segments():
    payload = _make_similar_payload(
        [
            _make_similar_item("x" * 81),
            _make_similar_item("2", source="s" * 90),
        ]
    )

    embed, view = create_similar_results_message(payload)

    assert isinstance(embed, discord.Embed)
    assert view is None


def test_create_similar_results_message_fails_closed_when_embed_fields_would_truncate_results():
    payload = _make_similar_payload(
        [_make_similar_item(str(i), source="leetcode", difficulty="Easy") | {"title": "T" * 300} for i in range(1, 6)]
    )

    embed, view = create_similar_results_message(payload)

    assert isinstance(embed, discord.Embed)
    assert view is None


@pytest.mark.asyncio
async def test_create_similar_results_message_normalizes_trimmed_button_segments():
    payload = _make_similar_payload(
        [
            _make_similar_item(" 42 ", source=" leetcode "),
            _make_similar_item(" 43 ", source=" atcoder ", difficulty=""),
        ]
    )

    embed, view = create_similar_results_message(payload)

    assert isinstance(embed, discord.Embed)
    assert view is not None
    assert [item.label for item in view.children] == ["42", "43"]
    assert [item.custom_id for item in view.children] == [
        "problem|leetcode|42|view",
        "problem|atcoder|43|view",
    ]


@pytest.mark.asyncio
async def test_create_similar_results_message_supports_exact_25_button_boundary():
    payload = _make_similar_payload([_make_similar_item(str(i)) for i in range(1, 26)])

    embed, view = create_similar_results_message(payload)

    assert isinstance(embed, discord.Embed)
    assert view is not None
    assert len(view.children) == 25
    assert max(item.row for item in view.children) == 4
    assert [item.row for item in view.children[:6]] == [0, 0, 0, 0, 0, 1]
    assert view.children[-1].row == 4
