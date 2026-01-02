import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

sys.path.insert(0, str(Path(__file__).parent.parent))

from cogs.slash_commands_cog import SlashCommandsCog


def _make_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    user = MagicMock()
    user.name = "tester"
    user.display_name = "tester"
    user.display_avatar = MagicMock(url="https://example.com/avatar.png")
    interaction.user = user
    return interaction


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.lcus = MagicMock()
    bot.lccn = MagicMock()
    bot.lcus.problems_db = MagicMock()
    return bot


def _make_atcoder_problem(problem_id: str) -> dict:
    return {
        "id": problem_id,
        "source": "atcoder",
        "slug": problem_id,
        "title": "Sample",
        "title_cn": "",
        "difficulty": None,
        "ac_rate": None,
        "rating": None,
        "contest": "abc436",
        "problem_index": "G",
        "tags": None,
        "link": f"https://atcoder.jp/contests/abc436/tasks/{problem_id}",
        "category": "Algorithms",
        "paid_only": 0,
        "content": None,
        "content_cn": None,
        "similar_questions": None,
    }


@pytest.mark.asyncio
async def test_problem_command_atcoder_single_sends_without_view():
    bot = _make_bot()
    bot.lcus.problems_db.get_problem.return_value = _make_atcoder_problem("abc436_g")
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.problem_command.callback(
        cog,
        interaction,
        problem_ids="abc436_g",
        domain="com",
        public=False,
        message=None,
        title=None,
        source=None,
    )

    assert interaction.followup.send.call_count == 1
    _, kwargs = interaction.followup.send.call_args
    assert "view" not in kwargs


@pytest.mark.asyncio
async def test_problem_command_atcoder_multiple_sends_without_view():
    bot = _make_bot()

    def _lookup(problem_id=None, source=None, **kwargs):
        return _make_atcoder_problem(problem_id)

    bot.lcus.problems_db.get_problem.side_effect = _lookup
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.problem_command.callback(
        cog,
        interaction,
        problem_ids="abc436_g,abc436_f",
        domain="com",
        public=False,
        message=None,
        title=None,
        source=None,
    )

    assert interaction.followup.send.call_count == 1
    _, kwargs = interaction.followup.send.call_args
    assert "view" not in kwargs
