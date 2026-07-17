import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, sentinel

import discord
import pytest
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.cogs import slash_commands_cog as slash_commands_module
from bot.cogs.slash_commands_cog import SlashCommandsCog
from bot.utils.ui_helpers import (
    create_problem_view,
    create_problems_overview_embed,
    create_problems_overview_view,
    is_embed_within_limits,
)


def _problem(problem_id: str, *, source: str = "codeforces") -> dict:
    return {
        "id": problem_id,
        "source": source,
        "slug": problem_id,
        "title": f"Problem {problem_id}",
        "difficulty": None,
        "ac_rate": None,
        "rating": 1200,
        "tags": ["implementation"],
        "link": f"https://example.com/{problem_id}",
    }


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.api = AsyncMock()
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key.format(**kwargs))
    return bot


def _make_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock(name="tester", display_name="tester")
    interaction.user.name = "tester"
    interaction.guild = MagicMock(id=123)
    interaction.guild_locale = None
    interaction.locale = discord.Locale.taiwan_chinese
    return interaction


def _payload(source: str, problems: list[dict]) -> dict:
    return {
        "challenge_info": problems[0],
        "problems": problems,
        "history_problems": [],
        "resolved_date": "2026-06-02",
        "daily_source": source,
    }


@pytest.mark.asyncio
async def test_daily_overview_view_preserves_exact_25_problem_order():
    problems = [_problem(str(index)) for index in range(1, 26)]

    view = create_problems_overview_view(problems, "com")

    assert view is not None
    assert [button.label for button in view.children] == [str(index) for index in range(1, 26)]
    assert [button.row for button in view.children[:6]] == [0, 0, 0, 0, 0, 1]
    assert view.children[-1].row == 4


@pytest.mark.asyncio
async def test_daily_overview_view_rejects_more_than_25_problems():
    problems = [_problem(str(index)) for index in range(1, 27)]

    assert create_problems_overview_view(problems, "com") is None


@pytest.mark.asyncio
async def test_daily_overview_view_rejects_unsafe_routing_fields():
    problems = [_problem("100A"), _problem("bad|id")]

    assert create_problems_overview_view(problems, "com") is None


@pytest.mark.asyncio
async def test_daily_overview_view_rejects_id_that_overflows_follow_up_action():
    problem = _problem("x" * 72)

    assert len(f"problem|codeforces|{problem['id']}|view") == 96
    assert len(f"problem|codeforces|{problem['id']}|translate") == 101
    assert create_problems_overview_view([problem], "com") is None


@pytest.mark.asyncio
async def test_daily_overview_view_accepts_longest_safe_follow_up_action():
    problem = _problem("x" * 71)

    view = create_problems_overview_view([problem], "com")
    detail_view = await create_problem_view(problem, _make_bot())

    assert view is not None
    assert len(f"problem|codeforces|{problem['id']}|translate") == 100
    assert max(len(button.custom_id) for button in detail_view.children) == 100


def test_daily_overview_view_can_require_explicit_source():
    problem = {key: value for key, value in _problem("100A").items() if key != "source"}

    assert create_problems_overview_view([problem], "com", default_source=None) is None


def test_daily_overview_embed_accepts_daily_footer_override():
    problems = [_problem("100A"), _problem("200B")]

    embed = create_problems_overview_embed(
        problems,
        "com",
        title="Sheep Daily | 2026-06-02",
        source_label="Sheep",
        footer_icon_url=None,
        footer_text="Sheep Daily | 2026-06-02",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Sheep Daily | 2026-06-02"
    assert embed.footer.text == "Sheep Daily | 2026-06-02"


def test_overview_embed_rejects_total_length_when_individual_fields_fit():
    embed = discord.Embed()
    for index in range(6):
        embed.add_field(name=str(index), value="x" * 1000)

    assert all(len(field.value) <= 1024 for field in embed.fields)
    assert len(embed) > 6000
    assert is_embed_within_limits(embed) is False


def test_daily_extra_source_choices_are_exact():
    source_parameter = next(
        parameter for parameter in SlashCommandsCog.daily_extra_command.parameters if parameter.name == "source"
    )

    assert [(choice.name, choice.value) for choice in source_parameter.choices] == [
        ("Sheep", "sheep"),
        ("0x3f", "0x3f"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "date", "public"),
    [
        ("sheep", None, False),
        ("0x3f", "2026-06-02", True),
    ],
)
async def test_daily_extra_single_problem_uses_source_payload_and_visibility(
    monkeypatch,
    source,
    date,
    public,
):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    problem = _problem("100A")
    get_payload = AsyncMock(return_value=_payload(source, [problem]))
    create_embed = AsyncMock(return_value=sentinel.embed)
    create_view = AsyncMock(return_value=sentinel.view)
    monkeypatch.setattr(slash_commands_module, "get_daily_payload", get_payload)
    monkeypatch.setattr(slash_commands_module, "create_problem_embed", create_embed)
    monkeypatch.setattr(slash_commands_module, "create_problem_view", create_view)

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source=source,
        date=date,
        public=public,
    )

    interaction.response.defer.assert_awaited_once_with(ephemeral=not public)
    get_payload.assert_awaited_once_with(bot, date_str=date, source=source)
    interaction.followup.send.assert_awaited_once_with(
        embed=sentinel.embed,
        view=sentinel.view,
        ephemeral=not public,
    )


@pytest.mark.asyncio
async def test_daily_extra_multiple_problems_uses_ordered_overview(monkeypatch):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    problems = [_problem("100A"), _problem("200B")]
    monkeypatch.setattr(
        slash_commands_module,
        "get_daily_payload",
        AsyncMock(return_value=_payload("sheep", problems)),
    )
    embed = discord.Embed(title="Safe overview")
    overview_embed = MagicMock(return_value=embed)
    overview_view = MagicMock(return_value=sentinel.view)
    monkeypatch.setattr(slash_commands_module, "create_problems_overview_embed", overview_embed)
    monkeypatch.setattr(slash_commands_module, "create_problems_overview_view", overview_view)

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date="2026-06-02",
        public=True,
    )

    assert overview_embed.call_args.args[0] == problems
    assert overview_view.call_args.args[0] == problems
    interaction.followup.send.assert_awaited_once_with(
        embed=embed,
        view=sentinel.view,
        ephemeral=False,
    )


@pytest.mark.asyncio
async def test_daily_extra_rejects_oversized_overview_embed(monkeypatch):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    problems = [_problem(str(index)) | {"title": "x" * 300} for index in range(5)]
    monkeypatch.setattr(
        slash_commands_module,
        "get_daily_payload",
        AsyncMock(return_value=_payload("sheep", problems)),
    )

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date="2026-06-02",
        public=False,
    )

    interaction.followup.send.assert_awaited_once_with(
        "errors.validation.daily_extra_unsafe_payload",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_daily_extra_rejects_invalid_date_before_api(monkeypatch):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    get_payload = AsyncMock()
    monkeypatch.setattr(slash_commands_module, "get_daily_payload", get_payload)

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date="2026/06/02",
        public=False,
    )

    get_payload.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(
        "errors.validation.date_format",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_daily_extra_reports_not_found(monkeypatch):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    monkeypatch.setattr(slash_commands_module, "get_daily_payload", AsyncMock(return_value=None))

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="0x3f",
        date="2026-06-02",
        public=False,
    )

    bot.i18n.t.assert_any_call(
        "errors.validation.daily_extra_not_found",
        "zh-TW",
        source_label="0x3f",
        date="2026-06-02",
    )
    assert interaction.followup.send.await_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_daily_extra_rejects_unsafe_multi_problem_payload(monkeypatch):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    problems = [_problem("100A"), _problem("bad|id")]
    monkeypatch.setattr(
        slash_commands_module,
        "get_daily_payload",
        AsyncMock(return_value=_payload("sheep", problems)),
    )
    monkeypatch.setattr(
        slash_commands_module,
        "create_problems_overview_view",
        MagicMock(return_value=None),
    )

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date="2026-06-02",
        public=False,
    )

    interaction.followup.send.assert_awaited_once_with(
        "errors.validation.daily_extra_unsafe_payload",
        ephemeral=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "problem",
    [
        {key: value for key, value in _problem("100A").items() if key != "source"},
        {key: value for key, value in _problem("100A").items() if key != "id"},
        _problem("100A", source="bad|source"),
        _problem("bad|id"),
        _problem("x" * 72),
    ],
)
async def test_daily_extra_rejects_unsafe_single_problem_payload(monkeypatch, problem):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    create_embed = AsyncMock(return_value=sentinel.embed)
    create_view = AsyncMock(return_value=sentinel.view)
    monkeypatch.setattr(
        slash_commands_module,
        "get_daily_payload",
        AsyncMock(return_value=_payload("sheep", [problem])),
    )
    monkeypatch.setattr(slash_commands_module, "create_problem_embed", create_embed)
    monkeypatch.setattr(slash_commands_module, "create_problem_view", create_view)

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date="2026-06-02",
        public=False,
    )

    interaction.followup.send.assert_awaited_once_with(
        "errors.validation.daily_extra_unsafe_payload",
        ephemeral=True,
    )
    create_embed.assert_not_awaited()
    create_view.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "error_kind"),
    [
        (ApiProcessingError("processing"), "processing"),
        (ApiNetworkError("network"), "network"),
        (ApiRateLimitError(5), "rate_limit"),
        (ApiError(500, "failed"), "generic"),
    ],
)
async def test_daily_extra_maps_api_errors(monkeypatch, exception, error_kind):
    bot = _make_bot()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    monkeypatch.setattr(
        slash_commands_module,
        "get_daily_payload",
        AsyncMock(side_effect=exception),
    )
    send_error = AsyncMock()
    monkeypatch.setattr(slash_commands_module, "send_api_error", send_error)

    await cog.daily_extra_command.callback(
        cog,
        interaction,
        source="sheep",
        date=None,
        public=False,
    )

    send_error.assert_awaited_once_with(
        interaction,
        error_kind,
        bot,
        ephemeral=True,
    )


def test_daily_extra_locale_keys_have_parity():
    locale_dir = Path(__file__).parents[1] / "src/bot/i18n/locales"
    documents = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in locale_dir.glob("*.json")}

    def flatten(value, prefix=""):
        keys = set()
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            if isinstance(child, dict):
                keys.update(flatten(child, path))
        return keys

    expected = flatten(documents["zh-TW"])
    required = {
        "commands.daily_extra.description",
        "commands.daily_extra.source",
        "commands.daily_extra.date",
        "commands.daily_extra.public",
        "errors.validation.daily_extra_not_found",
        "errors.validation.daily_extra_unsafe_payload",
        "ui.embed.daily_extra_title",
        "ui.embed.daily_extra_footer",
        "ui.embed.today",
    }
    assert required <= expected
    assert flatten(documents["en-US"]) == expected
    assert flatten(documents["zh-CN"]) == expected
