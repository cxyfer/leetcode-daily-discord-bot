import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest
import pytz
from discord.ext import commands

from bot.api_client import ApiDailyNotFoundError, ApiProcessingError
from bot.app import _create_reschedule_helper
from bot.cogs import schedule_manager_cog as schedule_module
from bot.cogs.schedule_manager_cog import ScheduleManagerCog


def _push(source: str, *, channel_id: int = 456, post_time: str = "09:30") -> dict:
    return {
        "server_id": 123,
        "source": source,
        "channel_id": channel_id,
        "role_id": 789,
        "post_time": post_time,
        "timezone": "UTC",
        "language": "zh-TW",
    }


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    bot.db = MagicMock()
    bot.logger = MagicMock()
    return bot


def test_scheduler_job_defaults_prevent_overlapping_daily_jobs():
    cog = ScheduleManagerCog(_make_bot())

    assert cog.scheduler._job_defaults["coalesce"] is True
    assert cog.scheduler._job_defaults["max_instances"] == 1
    assert cog.scheduler._job_defaults["misfire_grace_time"] == 300


@pytest.mark.asyncio
async def test_initialize_schedules_creates_one_job_per_push(monkeypatch):
    bot = _make_bot()
    bot.db.get_all_daily_pushes.return_value = [_push("leetcode.com"), _push("sheep"), _push("0x3f")]
    cog = ScheduleManagerCog(bot)
    monkeypatch.setattr(cog.scheduler, "start", MagicMock())
    monkeypatch.setattr(cog.scheduler, "remove_all_jobs", MagicMock())
    monkeypatch.setattr(cog.scheduler, "get_job", MagicMock(return_value=None))
    add_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "add_job", add_job)

    await cog.initialize_schedules()

    assert [item.kwargs["id"] for item in add_job.call_args_list] == [
        "daily_challenge:123:leetcode.com",
        "daily_challenge:123:sheep",
        "daily_challenge:123:0x3f",
    ]


@pytest.mark.asyncio
async def test_add_server_schedule_keeps_source_identity_and_misfire_grace_time(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    add_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "add_job", add_job)
    monkeypatch.setattr(cog.scheduler, "get_job", MagicMock(return_value=None))

    await cog.add_server_schedule(_push("sheep"))

    kwargs = add_job.call_args.kwargs
    assert kwargs["misfire_grace_time"] == 300
    assert kwargs["id"] == "daily_challenge:123:sheep"
    assert kwargs["args"] == [123, "sheep", 456, 789, "UTC"]


@pytest.mark.asyncio
async def test_invalid_push_does_not_prevent_peer_source_schedule(monkeypatch):
    bot = _make_bot()
    bot.db.get_all_daily_pushes.return_value = [_push("sheep", post_time="bad"), _push("0x3f")]
    cog = ScheduleManagerCog(bot)
    monkeypatch.setattr(cog.scheduler, "start", MagicMock())
    monkeypatch.setattr(cog.scheduler, "remove_all_jobs", MagicMock())
    monkeypatch.setattr(cog.scheduler, "get_job", MagicMock(return_value=None))
    add_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "add_job", add_job)

    await cog.initialize_schedules()

    add_job.assert_called_once()
    assert add_job.call_args.kwargs["id"] == "daily_challenge:123:0x3f"


@pytest.mark.asyncio
async def test_duplicate_scheduled_delivery_is_skipped_per_source(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    release = asyncio.Event()
    send_calls = 0

    async def send_daily_challenge(**kwargs):
        nonlocal send_calls
        send_calls += 1
        await release.wait()
        return {"title": "Two Sum"}

    monkeypatch.setattr(schedule_module, "send_daily_challenge", send_daily_challenge)

    first = asyncio.create_task(cog.send_daily_challenge_job(123, "sheep", 456, 789))
    await asyncio.sleep(0)
    duplicate = asyncio.create_task(cog.send_daily_challenge_job(123, "sheep", 456, 789))
    peer_source = asyncio.create_task(cog.send_daily_challenge_job(123, "0x3f", 456, 789))
    await asyncio.sleep(0)
    release.set()

    await asyncio.gather(first, duplicate, peer_source)

    assert send_calls == 2
    assert cog.scheduled_deliveries_in_progress == set()


@pytest.mark.asyncio
async def test_scheduled_delivery_forwards_source_and_uses_source_guard(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    fixed_utc = datetime(2026, 6, 2, 16, tzinfo=pytz.UTC)
    sent_kwargs = None

    async def send_daily_challenge(**kwargs):
        nonlocal sent_kwargs
        sent_kwargs = kwargs
        assert cog.scheduled_deliveries_in_progress == {(123, 456, "sheep", "2026-06-03")}
        return {"title": "Two Sum"}

    monkeypatch.setattr(schedule_module, "datetime", SimpleNamespace(now=lambda tz=None: fixed_utc.astimezone(tz)))
    monkeypatch.setattr(schedule_module, "send_daily_challenge", send_daily_challenge)

    await cog.send_daily_challenge_job(123, "sheep", 456, 789, "Asia/Taipei")

    assert sent_kwargs["daily_source"] == "sheep"
    assert "date_str" not in sent_kwargs


@pytest.mark.asyncio
async def test_scheduled_source_not_found_is_expected_skip(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    send = AsyncMock(side_effect=ApiDailyNotFoundError("0x3f"))
    monkeypatch.setattr(schedule_module, "send_daily_challenge", send)

    await cog.send_daily_challenge_job(123, "0x3f", 456)

    send.assert_awaited_once()
    assert cog.scheduled_deliveries_in_progress == set()


@pytest.mark.asyncio
async def test_processing_response_retries_source_delivery(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    send = AsyncMock(side_effect=[ApiProcessingError(), {"title": "Two Sum"}])
    sleep = AsyncMock()
    monkeypatch.setattr(schedule_module, "send_daily_challenge", send)
    monkeypatch.setattr(schedule_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(schedule_module.random, "uniform", lambda *_args: 0)

    await cog.send_daily_challenge_job(123, "sheep", 456)

    assert send.await_count == 2
    assert all(item.kwargs["daily_source"] == "sheep" for item in send.await_args_list)
    sleep.assert_awaited_once_with(2)


@pytest.mark.asyncio
async def test_scheduled_delivery_guard_cleans_up_after_exception(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    send = AsyncMock(side_effect=RuntimeError("discord send failed"))
    monkeypatch.setattr(schedule_module, "send_daily_challenge", send)

    await cog.send_daily_challenge_job(123, "leetcode.com", 456, 789)
    await cog.send_daily_challenge_job(123, "leetcode.com", 456, 789)

    assert send.await_count == 2
    assert cog.scheduled_deliveries_in_progress == set()


@pytest.mark.asyncio
async def test_targeted_source_removal_preserves_peer_jobs(monkeypatch):
    bot = _make_bot()
    bot.db.get_daily_push.return_value = None
    cog = ScheduleManagerCog(bot)
    get_job = MagicMock(return_value=object())
    remove_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "get_job", get_job)
    monkeypatch.setattr(cog.scheduler, "remove_job", remove_job)

    await cog.reschedule_daily_challenge(123, "sheep")

    get_job.assert_called_once_with("daily_challenge:123:sheep")
    remove_job.assert_called_once_with("daily_challenge:123:sheep")
    bot.db.get_daily_push.assert_called_once_with(123, "sheep")


@pytest.mark.asyncio
async def test_server_reschedule_rebuilds_all_source_jobs(monkeypatch):
    bot = _make_bot()
    bot.db.get_daily_pushes.return_value = [_push("leetcode.com"), _push("0x3f")]
    cog = ScheduleManagerCog(bot)
    monkeypatch.setattr(cog.scheduler, "get_job", MagicMock(return_value=object()))
    remove_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "remove_job", remove_job)
    add_schedule = AsyncMock()
    monkeypatch.setattr(cog, "add_server_schedule", add_schedule)

    await cog.reschedule_daily_challenge(123)

    assert remove_job.call_args_list == [
        call("daily_challenge:123:leetcode.com"),
        call("daily_challenge:123:sheep"),
        call("daily_challenge:123:0x3f"),
    ]
    assert [item.args[0]["source"] for item in add_schedule.await_args_list] == ["leetcode.com", "0x3f"]


@pytest.mark.asyncio
async def test_app_reschedule_helper_forwards_optional_source():
    bot = _make_bot()
    schedule_cog = SimpleNamespace(reschedule_daily_challenge=AsyncMock())
    bot.get_cog.return_value = schedule_cog
    helper = _create_reschedule_helper(bot)

    await helper(123, "config_update", source="sheep")

    schedule_cog.reschedule_daily_challenge.assert_awaited_once_with(123, "sheep")
