from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.api_client import ApiDailyNotFoundError, OjApiClient
from bot.utils import ui_helpers
from bot.utils.ui_helpers import get_daily_payload, send_daily_challenge


def _problem(problem_id: str, title: str) -> dict:
    return {
        "id": problem_id,
        "source": "codeforces",
        "slug": problem_id,
        "title": title,
        "difficulty": "1500",
        "rating": 1500,
        "tags": ["dp"],
        "link": f"https://codeforces.com/problemset/problem/{problem_id}",
    }


def _bot_with_daily(daily: dict):
    bot = MagicMock(spec=commands.Bot)
    bot.api = SimpleNamespace(get_daily=AsyncMock(return_value=daily))
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key.format(**kwargs))
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    channel = MagicMock()
    channel.send = AsyncMock()
    channel.guild.get_role.return_value = None
    bot.get_channel.return_value = channel
    return bot, channel


@pytest.mark.asyncio
async def test_api_client_get_daily_uses_source_without_domain():
    client = OjApiClient("https://example.test/api/v1")
    client._request = AsyncMock(return_value={"date": "2026-06-09", "source": "sheep", "problems": []})

    await client.get_daily(date="2026-06-09", source="sheep")

    client._request.assert_awaited_once_with(
        "GET",
        "daily",
        params={"source": "sheep", "date": "2026-06-09"},
    )


@pytest.mark.asyncio
async def test_api_client_get_daily_preserves_domain_calls():
    client = OjApiClient("https://example.test/api/v1")
    client._request = AsyncMock(return_value={"id": "1"})

    await client.get_daily("cn", "2026-06-09")

    client._request.assert_awaited_once_with(
        "GET",
        "daily",
        params={"domain": "cn", "date": "2026-06-09"},
    )


@pytest.mark.asyncio
async def test_api_client_distinguishes_missing_additional_source():
    client = OjApiClient("https://example.test/api/v1")
    client._request = AsyncMock(return_value=None)

    with pytest.raises(ApiDailyNotFoundError):
        await client.get_daily(source="0x3f")


@pytest.mark.asyncio
async def test_daily_payload_cache_is_isolated_by_source(monkeypatch):
    responses = {
        "sheep": {"date": "2026-06-09", "source": "sheep", "problems": [_problem("1A", "A")]},
        "0x3f": {"date": "2026-06-09", "source": "0x3f", "problems": [_problem("2B", "B")]},
    }
    bot, _ = _bot_with_daily(responses["sheep"])

    async def get_daily(*_args, source=None, **_kwargs):
        return responses[source]

    bot.api.get_daily.side_effect = get_daily
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda _anchor: [])

    sheep = await get_daily_payload(bot, date_str="2026-06-09", source="sheep")
    zero_x3f = await get_daily_payload(bot, date_str="2026-06-09", source="0x3f")
    sheep_again = await get_daily_payload(bot, date_str="2026-06-09", source="sheep")

    assert sheep["challenge_info"]["id"] == "1A"
    assert zero_x3f["challenge_info"]["id"] == "2B"
    assert sheep_again is sheep
    assert bot.api.get_daily.await_count == 2


@pytest.mark.asyncio
async def test_multi_problem_source_uses_existing_overview_helpers(monkeypatch):
    daily = {
        "date": "2026-06-09",
        "source": "sheep",
        "problems": [_problem("1A", "A"), _problem("2B", "B")],
    }
    bot, channel = _bot_with_daily(daily)
    overview_embed = discord.Embed(title="Sheep Daily")
    overview_view = MagicMock()
    create_overview_embed = MagicMock(return_value=overview_embed)
    create_overview_view = MagicMock(return_value=overview_view)
    create_problem_embed = AsyncMock()
    monkeypatch.setattr(ui_helpers, "create_problems_overview_embed", create_overview_embed)
    monkeypatch.setattr(ui_helpers, "create_problems_overview_view", create_overview_view)
    monkeypatch.setattr(ui_helpers, "create_problem_embed", create_problem_embed)

    result = await send_daily_challenge(bot=bot, channel_id=123, daily_source="sheep", guild_locale="zh-TW")

    bot.api.get_daily.assert_awaited_once_with(source="sheep")
    create_overview_embed.assert_called_once()
    create_overview_view.assert_called_once_with(daily["problems"], "com")
    create_problem_embed.assert_not_awaited()
    channel.send.assert_awaited_once_with(content=None, embed=overview_embed, view=overview_view)
    assert result["id"] == "1A"


@pytest.mark.asyncio
async def test_single_problem_source_preserves_daily_problem_rendering(monkeypatch):
    problem = _problem("1A", "A")
    daily = {"date": "2026-06-09", "source": "sheep", "problems": [problem]}
    bot, channel = _bot_with_daily(daily)
    problem_embed = discord.Embed(title="A")
    problem_view = MagicMock()
    create_problem_embed = AsyncMock(return_value=problem_embed)
    create_problem_view = AsyncMock(return_value=problem_view)
    create_overview_embed = MagicMock()
    monkeypatch.setattr(ui_helpers, "create_problem_embed", create_problem_embed)
    monkeypatch.setattr(ui_helpers, "create_problem_view", create_problem_view)
    monkeypatch.setattr(ui_helpers, "create_problems_overview_embed", create_overview_embed)

    await send_daily_challenge(bot=bot, channel_id=123, daily_source="sheep", guild_locale="zh-TW")

    create_problem_embed.assert_awaited_once()
    create_problem_view.assert_awaited_once()
    create_overview_embed.assert_not_called()
    channel.send.assert_awaited_once_with(content=None, embed=problem_embed, view=problem_view)


@pytest.mark.asyncio
async def test_source_delivery_preserves_role_mention(monkeypatch):
    problem = _problem("1A", "A")
    daily = {"date": "2026-06-09", "source": "sheep", "problems": [problem]}
    bot, channel = _bot_with_daily(daily)
    role = SimpleNamespace(mention="<@&456>")
    channel.guild.get_role.return_value = role
    monkeypatch.setattr(ui_helpers, "create_problem_embed", AsyncMock(return_value=discord.Embed(title="A")))
    monkeypatch.setattr(ui_helpers, "create_problem_view", AsyncMock(return_value=MagicMock()))

    await send_daily_challenge(
        bot=bot,
        channel_id=123,
        role_id=456,
        daily_source="sheep",
        guild_locale="zh-TW",
    )

    assert channel.send.await_args.kwargs["content"] == "<@&456>"


@pytest.mark.asyncio
async def test_scheduled_source_delivery_propagates_not_found():
    bot, _ = _bot_with_daily({})
    bot.api.get_daily.side_effect = ApiDailyNotFoundError("0x3f")

    with pytest.raises(ApiDailyNotFoundError, match="0x3f"):
        await send_daily_challenge(bot=bot, channel_id=123, daily_source="0x3f", guild_locale="zh-TW")
