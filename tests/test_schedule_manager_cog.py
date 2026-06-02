import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from discord.ext import commands

from bot.cogs import schedule_manager_cog as schedule_module
from bot.cogs.schedule_manager_cog import ScheduleManagerCog


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    return bot


def test_scheduler_job_defaults_prevent_overlapping_daily_jobs():
    cog = ScheduleManagerCog(_make_bot())

    assert cog.scheduler._job_defaults["coalesce"] is True
    assert cog.scheduler._job_defaults["max_instances"] == 1
    assert cog.scheduler._job_defaults["misfire_grace_time"] == 300


@pytest.mark.asyncio
async def test_add_server_schedule_keeps_misfire_grace_time(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    add_job = MagicMock()
    monkeypatch.setattr(cog.scheduler, "add_job", add_job)
    monkeypatch.setattr(cog.scheduler, "get_job", MagicMock(return_value=None))

    await cog.add_server_schedule(
        {
            "server_id": 123,
            "channel_id": 456,
            "role_id": 789,
            "post_time": "09:30",
            "timezone": "UTC",
        }
    )

    assert add_job.call_args.kwargs["misfire_grace_time"] == 300
    assert add_job.call_args.kwargs["id"] == "daily_challenge_123"


@pytest.mark.asyncio
async def test_duplicate_scheduled_delivery_is_skipped(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())
    release = asyncio.Event()
    send_calls = 0

    async def send_daily_challenge(**kwargs):
        nonlocal send_calls
        send_calls += 1
        await release.wait()
        return {"title": "Two Sum"}

    monkeypatch.setattr(schedule_module, "send_daily_challenge", send_daily_challenge)

    first = asyncio.create_task(cog.send_daily_challenge_job(123, 456, 789))
    await asyncio.sleep(0)
    second = asyncio.create_task(cog.send_daily_challenge_job(123, 456, 789))
    await asyncio.sleep(0)
    release.set()

    await asyncio.gather(first, second)

    assert send_calls == 1
    assert cog.scheduled_deliveries_in_progress == set()


@pytest.mark.asyncio
async def test_scheduled_delivery_guard_cleans_up_after_exception(monkeypatch):
    cog = ScheduleManagerCog(_make_bot())

    async def send_daily_challenge(**kwargs):
        raise RuntimeError("discord send failed")

    monkeypatch.setattr(schedule_module, "send_daily_challenge", send_daily_challenge)

    await cog.send_daily_challenge_job(123, 456, 789)

    assert cog.scheduled_deliveries_in_progress == set()

    await cog.send_daily_challenge_job(123, 456, 789)
    assert cog.scheduled_deliveries_in_progress == set()
