import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

sys.path.insert(0, str(Path(__file__).parent.parent))

from cogs.slash_commands_cog import SlashCommandsCog
from utils.ui_constants import NON_DIFFICULTY_EMOJI


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
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    bot.ATCODER_DESCRIPTION_BUTTON_PREFIX = "atcoder_problem|"
    bot.ATCODER_TRANSLATE_BUTTON_PREFIX = "atcoder_translate|"
    bot.ATCODER_INSPIRE_BUTTON_PREFIX = "atcoder_inspire|"
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
    assert "view" in kwargs
    assert len(kwargs["view"].children) == 3
    assert kwargs["view"].children[0].custom_id.startswith("atcoder_problem|")


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
    assert "view" in kwargs
    assert len(kwargs["view"].children) == 2
    for button in kwargs["view"].children:
        emoji_value = (
            button.emoji.name if hasattr(button.emoji, "name") else str(button.emoji)
        )
        assert emoji_value == NON_DIFFICULTY_EMOJI
        assert button.custom_id.startswith("problem_detail|atcoder|")
