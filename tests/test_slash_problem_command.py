from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.cogs.slash_commands_cog import SlashCommandsCog
from bot.utils.ui_constants import (
    LUOGU_DIFFICULTY_COLORS,
    LUOGU_DIFFICULTY_EMOJIS,
    MAX_DAILY_SIMILAR_FIELD_LENGTH,
    NON_DIFFICULTY_EMOJI,
)
from bot.utils.ui_helpers import create_problem_embed


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
    interaction.guild = MagicMock()
    interaction.guild.id = 987654321
    interaction.guild_locale = None
    interaction.locale = discord.Locale.taiwan_chinese
    return interaction


_I18N_VALUES = {
    "ui.embed.difficulty": "Difficulty",
    "ui.embed.rating": "Rating",
    "ui.embed.ac_rate": "AC Rate",
    "ui.embed.tags": "Tags",
    "ui.embed.source": "Source",
    "ui.embed.similar_questions": "Similar Questions ({count}{suffix})",
    "ui.embed.history_problems": "History Problems",
    "ui.embed.daily_footer": "LeetCode Daily Challenge | {date}",
    "ui.embed.problem_footer": "LeetCode Problem",
    "ui.embed.description_author": "LeetCode Problem",
    "ui.embed.atcoder_problem": "AtCoder Problem",
    "ui.embed.solve_on": "> Solve on [{alt_name} ({alt_full_name})]({link}).",
    "ui.embed.similar_title": "🔍 相似題目",
    "ui.embed.rewritten_search": "✨ 重寫搜尋",
    "ui.embed.base_problem": "🔗 基準題目",
    "ui.embed.results": "Results",
    "ui.embed.instructions": "Instructions",
    "ui.embed.instructions_text": "Click the buttons below to view detailed information for each problem.",
    "ui.embed.problems": "Problems",
    "ui.embed.problems_part": "Part {number}",
    "ui.embed.problems_overview": "{source_label} Problems Overview",
    "ui.embed.problems_found": "🔍 {source_label} Problems ({count} found)",
    "ui.embed.submission_author": "{username}'s Recent Submissions",
    "ui.embed.submission_footer": "Problem {current} of {total}",
    "ui.buttons.description": "題目描述",
    "ui.buttons.translate": "LLM 翻譯",
    "ui.buttons.inspire": "靈感啟發",
    "ui.buttons.similar": "相似題目",
    "ui.buttons.confirm_reset": "確認重置",
    "ui.buttons.cancel": "取消",
    "ui.inspire.title": "💡 靈感啟發",
    "ui.inspire.thinking": "🧠 思路",
    "ui.inspire.traps": "⚠️ 陷阱",
    "ui.inspire.algorithms": "🛠️ 推薦演算法",
    "ui.inspire.inspiration": "✨ 其他靈感",
    "ui.inspire.footer": "由 {model} 提供靈感",
    "ui.inspire.default_footer": "Problem {id} 靈感啟發",
    "ui.settings.title": "{guild_name} 的 LeetCode 挑戰設定",
    "ui.settings.channel": "發送頻道",
    "ui.settings.role": "標記身分組",
    "ui.settings.time": "發送時間",
    "ui.settings.not_set": "未設定",
    "ui.settings.unknown_channel": "未知頻道 (ID: {id})",
    "ui.settings.unknown_role": "未知身分組 (ID: {id})",
}


def _i18n_t(key, locale, **kwargs):
    template = _I18N_VALUES.get(key, key)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.api = AsyncMock()
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    bot.config = MagicMock()
    bot.config.default_locale = "zh-TW"
    bot.i18n = MagicMock()
    bot.i18n.t = MagicMock(side_effect=_i18n_t)
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
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


def _make_luogu_problem(problem_id: str, difficulty: str = "入门") -> dict:
    return {
        "id": problem_id,
        "source": "luogu",
        "slug": problem_id,
        "title": f"Luogu {problem_id}",
        "title_cn": "",
        "difficulty": difficulty,
        "ac_rate": None,
        "rating": None,
        "contest": None,
        "problem_index": None,
        "tags": None,
        "link": f"https://www.luogu.com.cn/problem/{problem_id}",
        "category": "Algorithms",
        "paid_only": 0,
        "content": None,
        "content_cn": None,
        "similar_questions": None,
    }


@pytest.mark.asyncio
async def test_problem_command_atcoder_single_sends_with_full_problem_view():
    bot = _make_bot()
    bot.api.resolve.return_value = {"problem": _make_atcoder_problem("abc436_g")}
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
    assert len(kwargs["view"].children) == 4
    assert kwargs["view"].children[0].custom_id == "problem|atcoder|abc436_g|desc"


@pytest.mark.asyncio
async def test_problem_command_atcoder_multiple_sends_overview_buttons():
    bot = _make_bot()

    async def _resolve(query):
        return {"problem": _make_atcoder_problem(query)}

    bot.api.resolve.side_effect = _resolve
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
        emoji_value = button.emoji.name if hasattr(button.emoji, "name") else str(button.emoji)
        assert emoji_value == NON_DIFFICULTY_EMOJI
        assert button.custom_id.startswith("problem|atcoder|")
        assert button.custom_id.endswith("|view")


@pytest.mark.asyncio
async def test_problem_command_luogu_single_shows_difficulty_card():
    bot = _make_bot()
    bot.api.resolve.return_value = {"problem": _make_luogu_problem("P1001", difficulty="入门")}
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.problem_command.callback(
        cog,
        interaction,
        problem_ids="P1001",
        domain="com",
        public=False,
        message=None,
        title=None,
        source="luogu",
    )

    assert interaction.followup.send.call_count == 1
    _, kwargs = interaction.followup.send.call_args
    embed = kwargs["embed"]
    difficulty_field = next(field for field in embed.fields if field.name == "🔥 Difficulty")

    assert embed.title == f"{LUOGU_DIFFICULTY_EMOJIS['入门']} P1001: Luogu P1001"
    assert embed.color.value == LUOGU_DIFFICULTY_COLORS["入门"]
    assert difficulty_field.value == "**入门**"
    assert kwargs["view"].children[0].custom_id == "problem|luogu|P1001|desc"


@pytest.mark.asyncio
async def test_problem_command_luogu_multiple_uses_difficulty_emojis():
    bot = _make_bot()

    async def _resolve(query):
        problems = {
            "luogu:P1001": _make_luogu_problem("P1001", difficulty="入门"),
            "luogu:P1002": _make_luogu_problem("P1002", difficulty="普及/提高-"),
        }
        return {"problem": problems[query]}

    bot.api.resolve.side_effect = _resolve
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.problem_command.callback(
        cog,
        interaction,
        problem_ids="P1001,P1002",
        domain="com",
        public=False,
        message=None,
        title=None,
        source="luogu",
    )

    assert interaction.followup.send.call_count == 1
    _, kwargs = interaction.followup.send.call_args
    overview_field = kwargs["embed"].fields[0]
    button_emojis = [
        button.emoji.name if hasattr(button.emoji, "name") else str(button.emoji) for button in kwargs["view"].children
    ]

    assert kwargs["embed"].footer.text == "Luogu Problems Overview"
    assert f"{LUOGU_DIFFICULTY_EMOJIS['入门']} **[P1001: Luogu P1001]" in overview_field.value
    assert f"{LUOGU_DIFFICULTY_EMOJIS['普及/提高-']} **[P1002: Luogu P1002]" in overview_field.value
    assert button_emojis == [LUOGU_DIFFICULTY_EMOJIS["入门"], LUOGU_DIFFICULTY_EMOJIS["普及/提高-"]]
    assert all(button.custom_id.startswith("problem|luogu|") for button in kwargs["view"].children)
    assert all(button.custom_id.endswith("|view") for button in kwargs["view"].children)


@pytest.mark.asyncio
async def test_create_problem_embed_formats_daily_similar_questions_with_id_link_and_rating():
    bot = _make_bot()
    problem = {
        "id": "1",
        "source": "leetcode",
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "Easy",
        "ac_rate": 52.34,
        "rating": 1234,
        "tags": ["Array", "Hash Table"],
        "link": "https://leetcode.com/problems/two-sum/",
        "similar_questions": [
            {
                "id": "48",
                "source": "leetcode",
                "slug": "rotate-image",
                "title": "Rotate Image",
                "difficulty": "Medium",
                "rating": 2010,
                "link": "https://leetcode.com/problems/rotate-image/",
            }
        ],
    }

    embed = await create_problem_embed(problem_info=problem, bot=bot, is_daily=True)

    similar_field = next(field for field in embed.fields if field.name == "Similar Questions (1)")
    assert similar_field.value == "- 🟡 [48. Rotate Image](https://leetcode.com/problems/rotate-image/) *2010*"


@pytest.mark.asyncio
async def test_create_problem_embed_packs_all_daily_similar_questions_within_length_budget():
    bot = _make_bot()
    long_title = "B" * 180
    similar_questions = []
    for i in range(1, 10):
        similar_questions.append(
            {
                "id": str(100 + i),
                "source": "leetcode",
                "slug": f"sample-problem-{i}",
                "title": f"{long_title}-{i}",
                "difficulty": "Medium",
                "rating": 1800 + i,
                "link": f"https://leetcode.com/problems/sample-problem-{i}/",
            }
        )

    problem = {
        "id": "1",
        "source": "leetcode",
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "Easy",
        "ac_rate": 52.34,
        "rating": 1234,
        "tags": ["Array"],
        "link": "https://leetcode.com/problems/two-sum/",
        "similar_questions": similar_questions,
    }

    embed = await create_problem_embed(problem_info=problem, bot=bot, is_daily=True)

    similar_field = next(field for field in embed.fields if field.name == "Similar Questions (3+)")
    lines = similar_field.value.split("\n")

    assert len(similar_field.value) <= MAX_DAILY_SIMILAR_FIELD_LENGTH
    assert len(lines) > 3
    assert lines[0].startswith("- 🟡 [101. ")
    assert similar_field.value.endswith("...")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("slug_key", "slug_value"),
    [("titleSlug", "rotate-image"), ("slug", "best-time-to-buy-and-sell-stock")],
)
async def test_create_problem_embed_builds_daily_similar_question_link_from_slug_when_link_missing(
    slug_key: str, slug_value: str
):
    bot = _make_bot()
    problem = {
        "id": "1",
        "source": "leetcode",
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "Easy",
        "ac_rate": 52.34,
        "rating": 1234,
        "tags": ["Array"],
        "link": "https://leetcode.com/problems/two-sum/",
        "similar_questions": [
            {
                "id": "48",
                "source": "leetcode",
                "title": "Similar Problem",
                "difficulty": "Medium",
                slug_key: slug_value,
            }
        ],
    }

    embed = await create_problem_embed(problem_info=problem, bot=bot, is_daily=True)

    similar_field = next(field for field in embed.fields if field.name == "Similar Questions (1)")
    assert similar_field.value == f"- 🟡 [48. Similar Problem](https://leetcode.com/problems/{slug_value}/)"
