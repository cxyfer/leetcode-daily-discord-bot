import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.utils import ui_helpers
from bot.utils.ui_helpers import get_daily_payload, send_daily_challenge


@pytest.fixture(autouse=True)
def clear_daily_payload_state():
    ui_helpers._DAILY_PAYLOAD_CACHE.clear()
    ui_helpers._DAILY_PAYLOAD_IN_FLIGHT.clear()
    yield
    ui_helpers._DAILY_PAYLOAD_CACHE.clear()
    ui_helpers._DAILY_PAYLOAD_IN_FLIGHT.clear()


def _daily_problem(date: str = "2026-06-03") -> dict:
    return {
        "id": "1",
        "source": "leetcode",
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "Easy",
        "ac_rate": 52.34,
        "rating": 1234,
        "tags": ["Array"],
        "link": "https://leetcode.com/problems/two-sum/",
        "date": date,
    }


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.api = SimpleNamespace(get_daily=AsyncMock(return_value=_daily_problem()))
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key.format(**kwargs))
    return bot


def _make_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.guild = MagicMock()
    interaction.guild.id = 123
    interaction.guild_locale = None
    interaction.locale = discord.Locale.taiwan_chinese
    return interaction


@pytest.mark.asyncio
async def test_get_daily_payload_coalesces_concurrent_identical_requests(monkeypatch):
    bot = _make_bot()
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def fetch_daily(domain, date=None):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return _daily_problem(date or "2026-06-03")

    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
    bot.api.get_daily.side_effect = fetch_daily

    first = asyncio.create_task(get_daily_payload(bot, "com", "2026-06-03"))
    await started.wait()
    second = asyncio.create_task(get_daily_payload(bot, "com", "2026-06-03"))
    release.set()

    first_payload, second_payload = await asyncio.gather(first, second)

    assert first_payload is second_payload
    assert first_payload["challenge_info"]["id"] == "1"
    assert calls == 1


@pytest.mark.asyncio
async def test_get_daily_payload_reuses_short_lived_cache(monkeypatch):
    bot = _make_bot()
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])

    first_payload = await get_daily_payload(bot, "com", "2026-06-03")
    second_payload = await get_daily_payload(bot, "com", "2026-06-03")

    assert first_payload is second_payload
    assert bot.api.get_daily.await_count == 1


@pytest.mark.asyncio
async def test_send_daily_challenge_sends_each_manual_response_from_cached_payload(monkeypatch):
    bot = _make_bot()
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
    first_interaction = _make_interaction()
    second_interaction = _make_interaction()

    await send_daily_challenge(bot=bot, interaction=first_interaction, domain="com", ephemeral=True)
    await send_daily_challenge(bot=bot, interaction=second_interaction, domain="com", ephemeral=False)

    assert bot.api.get_daily.await_count == 1
    first_interaction.followup.send.assert_awaited_once()
    second_interaction.followup.send.assert_awaited_once()
    assert first_interaction.followup.send.await_args.kwargs["ephemeral"] is True
    assert second_interaction.followup.send.await_args.kwargs["ephemeral"] is False
