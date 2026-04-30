from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.cogs import similar_cog as similar_cog_module
from bot.cogs.similar_cog import SimilarCog
from bot.utils.config import SimilarConfig


def _make_interaction() -> AsyncMock:
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild.id = 987654321
    interaction.guild_locale = None
    interaction.locale = discord.Locale.taiwan_chinese
    return interaction


def _make_bot() -> MagicMock:
    bot = MagicMock(spec=commands.Bot)
    bot.api = AsyncMock()
    bot.config = MagicMock()
    bot.config.default_locale = "zh-TW"
    bot.config.get_similar_config.return_value = SimilarConfig(top_k=25, min_similarity=0.7)
    bot.i18n = MagicMock()
    bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key)
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    return bot


@pytest.mark.asyncio
async def test_similar_command_clamps_top_k_and_uses_shared_message_builder(monkeypatch):
    bot = _make_bot()
    bot.api.search_similar_by_text.return_value = {
        "results": [
            {
                "id": "1",
                "source": "leetcode",
                "title": "Two Sum",
                "difficulty": "Easy",
                "similarity": 0.91,
                "link": "https://example.com/1",
            }
        ]
    }
    interaction = _make_interaction()
    cog = SimilarCog(bot)
    sentinel_embed = discord.Embed(title="sentinel")
    sentinel_view = SimpleNamespace(children=[])
    helper_calls = []

    def fake_create_similar_results_message(result, *, base_source=None, base_id=None, **kwargs):
        helper_calls.append((result, base_source, base_id))
        return sentinel_embed, sentinel_view

    monkeypatch.setattr(
        similar_cog_module, "create_similar_results_message", fake_create_similar_results_message, raising=False
    )

    await cog.similar_command.callback(
        cog,
        interaction,
        query="graph dp",
        problem=None,
        top_k=99,
        source=None,
        public=False,
    )

    bot.api.search_similar_by_text.assert_awaited_once_with("graph dp", None, 20, 0.7)
    assert helper_calls == [(bot.api.search_similar_by_text.return_value, None, None)]
    interaction.followup.send.assert_awaited_once_with(embed=sentinel_embed, view=sentinel_view, ephemeral=True)


@pytest.mark.asyncio
async def test_similar_command_problem_input_resolves_problem_and_passes_base_problem(monkeypatch):
    bot = _make_bot()
    bot.api.resolve.return_value = {
        "problem": {
            "id": "abc100_a",
            "source": "atcoder",
        }
    }
    bot.api.search_similar_by_id.return_value = {
        "results": [
            {
                "id": "abc100_b",
                "source": "atcoder",
                "title": "B",
                "difficulty": "",
                "similarity": 0.88,
                "link": "https://example.com/atcoder/abc100_b",
            }
        ]
    }
    interaction = _make_interaction()
    cog = SimilarCog(bot)
    sentinel_embed = discord.Embed(title="problem-path")
    sentinel_view = SimpleNamespace(children=[])
    helper_calls = []

    def fake_create_similar_results_message(result, *, base_source=None, base_id=None, **kwargs):
        helper_calls.append((result, base_source, base_id))
        return sentinel_embed, sentinel_view

    monkeypatch.setattr(
        similar_cog_module, "create_similar_results_message", fake_create_similar_results_message, raising=False
    )

    await cog.similar_command.callback(
        cog,
        interaction,
        query=None,
        problem="abc100_a",
        top_k=5,
        source=None,
        public=False,
    )

    bot.api.resolve.assert_awaited_once_with("abc100_a")
    bot.api.search_similar_by_id.assert_awaited_once_with("atcoder", "abc100_a", 5, 0.7)
    assert helper_calls == [(bot.api.search_similar_by_id.return_value, "atcoder", "abc100_a")]
    interaction.followup.send.assert_awaited_once_with(embed=sentinel_embed, view=sentinel_view, ephemeral=True)


@pytest.mark.asyncio
async def test_similar_command_safe_results_send_detail_button_view():
    bot = _make_bot()
    bot.api.search_similar_by_text.return_value = {
        "results": [
            {
                "id": "1",
                "source": "leetcode",
                "title": "Two Sum",
                "difficulty": "Easy",
                "similarity": 0.91,
                "link": "https://example.com/1",
            },
            {
                "id": "abc100_b",
                "source": "atcoder",
                "title": "B",
                "difficulty": "",
                "similarity": 0.88,
                "link": "https://example.com/abc100_b",
            },
        ]
    }
    interaction = _make_interaction()
    cog = SimilarCog(bot)

    await cog.similar_command.callback(
        cog,
        interaction,
        query="graph dp",
        problem=None,
        top_k=2,
        source=None,
        public=False,
    )

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["view"] is not None
    assert [item.custom_id for item in kwargs["view"].children] == [
        "problem|leetcode|1|view",
        "problem|atcoder|abc100_b|view",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("results", "label"),
    [
        (
            [
                {
                    "id": "bad|id",
                    "source": "leetcode",
                    "title": "Bad",
                    "difficulty": "Easy",
                    "similarity": 0.91,
                    "link": "https://example.com/bad",
                }
            ],
            "invalid",
        ),
        (
            [
                {
                    "id": str(i),
                    "source": "leetcode",
                    "title": f"P{i}",
                    "difficulty": "Easy",
                    "similarity": 0.91,
                    "link": f"https://example.com/{i}",
                }
                for i in range(1, 27)
            ],
            "overflow",
        ),
    ],
)
async def test_similar_command_unsafe_results_degrade_to_embed_only(results, label):
    bot = _make_bot()
    bot.api.search_similar_by_text.return_value = {"results": results}
    interaction = _make_interaction()
    cog = SimilarCog(bot)

    await cog.similar_command.callback(
        cog,
        interaction,
        query=label,
        problem=None,
        top_k=20,
        source=None,
        public=False,
    )

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["view"] is None
