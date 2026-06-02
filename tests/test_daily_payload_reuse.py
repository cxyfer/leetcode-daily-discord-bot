import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
import pytz
from discord.ext import commands

from bot.api_client import ApiProcessingError
from bot.utils import ui_helpers
from bot.utils.ui_helpers import get_daily_payload, send_daily_challenge


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
async def test_current_daily_payload_cache_is_scoped_to_fallback_date(monkeypatch):
    bot = _make_bot()
    dates = iter(
        [
            datetime(2026, 6, 2, tzinfo=pytz.UTC),
            datetime(2026, 6, 3, tzinfo=pytz.UTC),
        ]
    )
    fetched_dates = iter(["2026-06-02", "2026-06-03"])
    monkeypatch.setattr(ui_helpers, "datetime", SimpleNamespace(now=lambda tz=None: next(dates)))
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])

    async def fetch_daily(domain, date=None):
        return _daily_problem(next(fetched_dates))

    bot.api.get_daily.side_effect = fetch_daily

    first_payload = await get_daily_payload(bot, "com")
    second_payload = await get_daily_payload(bot, "com")

    assert first_payload["resolved_date"] == "2026-06-02"
    assert second_payload["resolved_date"] == "2026-06-03"
    assert bot.api.get_daily.await_count == 2


@pytest.mark.asyncio
async def test_get_daily_payload_ignores_completed_failed_in_flight_task(monkeypatch):
    bot = _make_bot()
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])

    async def failed_fetch():
        raise ApiProcessingError("processing")

    failed_task = asyncio.create_task(failed_fetch())
    with pytest.raises(ApiProcessingError):
        await failed_task

    bot._daily_payload_in_flight = {("com", "2026-06-03"): failed_task}

    payload = await get_daily_payload(bot, "com", "2026-06-03")

    assert payload["challenge_info"]["id"] == "1"
    assert bot.api.get_daily.await_count == 1


@pytest.mark.asyncio
async def test_get_daily_payload_cache_is_scoped_to_bot_instance(monkeypatch):
    first_bot = _make_bot()
    second_bot = _make_bot()
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])

    await get_daily_payload(first_bot, "com", "2026-06-03")
    await get_daily_payload(second_bot, "com", "2026-06-03")

    assert first_bot.api.get_daily.await_count == 1
    assert second_bot.api.get_daily.await_count == 1
    assert first_bot._daily_payload_cache is not second_bot._daily_payload_cache


@pytest.mark.asyncio
async def test_get_daily_payload_prunes_expired_cache_entries(monkeypatch):
    bot = _make_bot()
    old_payload = {
        "challenge_info": _daily_problem("2026-06-01"),
        "history_problems": [],
        "resolved_date": "2026-06-01",
    }
    bot._daily_payload_cache = {("com", "2026-06-01"): (0.0, old_payload)}
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
    monkeypatch.setattr(ui_helpers.time, "monotonic", lambda: 61.0)

    await get_daily_payload(bot, "com", "2026-06-03")

    assert ("com", "2026-06-01") not in bot._daily_payload_cache
    assert ("com", "2026-06-03") in bot._daily_payload_cache


@pytest.mark.asyncio
async def test_send_daily_challenge_uses_resolved_date_when_api_omits_date(monkeypatch):
    bot = _make_bot()
    problem = _daily_problem()
    problem.pop("date")
    bot.api.get_daily.return_value = problem
    fixed_now = datetime(2026, 6, 3, tzinfo=pytz.UTC)
    monkeypatch.setattr(ui_helpers, "datetime", SimpleNamespace(now=lambda tz=None: fixed_now))
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
    bot.i18n.t = MagicMock(
        side_effect=lambda key, locale, **kwargs: f"Daily | {kwargs['date']}" if key == "ui.embed.daily_footer" else key
    )
    interaction = _make_interaction()

    await send_daily_challenge(bot=bot, interaction=interaction, domain="com", ephemeral=True)

    embed = interaction.followup.send.await_args.kwargs["embed"]
    assert embed.footer.text == "Daily | 2026-06-03"


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


@pytest.mark.asyncio
async def test_current_daily_payload_does_not_pollute_explicit_fallback_date(monkeypatch):
    bot = _make_bot()
    fixed_now = datetime(2026, 6, 2, tzinfo=pytz.UTC)
    calls = []

    async def fetch_daily(domain, date=None):
        calls.append(date)
        problem = _daily_problem(date or "2026-06-02")
        problem["title"] = "Current" if date is None else "Explicit"
        if date is None:
            problem.pop("date")
        return problem

    monkeypatch.setattr(ui_helpers, "datetime", SimpleNamespace(now=lambda tz=None: fixed_now))
    monkeypatch.setattr(ui_helpers, "generate_history_dates", lambda anchor_date: [])
    bot.api.get_daily.side_effect = fetch_daily

    current_payload = await get_daily_payload(bot, "com")
    explicit_payload = await get_daily_payload(bot, "com", "2026-06-02")

    assert current_payload["challenge_info"]["title"] == "Current"
    assert explicit_payload["challenge_info"]["title"] == "Explicit"
    assert calls == [None, "2026-06-02"]


@pytest.mark.asyncio
async def test_get_daily_payload_shields_shared_fetch_from_waiter_cancellation(monkeypatch):
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

    first = asyncio.create_task(get_daily_payload(bot, "com"))
    await started.wait()
    second = asyncio.create_task(get_daily_payload(bot, "com"))
    first.cancel()

    with pytest.raises(asyncio.CancelledError):
        await first

    release.set()
    payload = await second

    assert payload["challenge_info"]["id"] == "1"
    assert calls == 1
