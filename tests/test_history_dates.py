"""
Unit tests for generate_history_dates helper.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.leetcode import generate_history_dates
from bot.utils.ui_helpers import _fetch_daily_history


def test_generate_history_dates_basic():
    assert generate_history_dates("2026-01-07") == [
        "2025-01-07",
        "2024-01-07",
        "2023-01-07",
        "2022-01-07",
        "2021-01-07",
    ]


def test_generate_history_dates_leap_day():
    assert generate_history_dates("2025-02-29") == [
        "2024-02-29",
        "2020-02-29",
    ]


def test_generate_history_dates_before_start_date():
    assert generate_history_dates("2021-03-15") == []


def test_generate_history_dates_no_history():
    assert generate_history_dates("2020-05-01") == []


def test_generate_history_dates_invalid_format():
    assert generate_history_dates("2026/01/07") == []


@pytest.mark.asyncio
async def test_fetch_daily_history_uses_module_level_generate_history_dates():
    bot = SimpleNamespace(api=SimpleNamespace(get_daily=AsyncMock(side_effect=lambda domain, day: {"date": day})))

    history = await _fetch_daily_history(bot, "com", "2026-01-07")

    assert [entry["date"] for entry in history] == [
        "2025-01-07",
        "2024-01-07",
        "2023-01-07",
        "2022-01-07",
        "2021-01-07",
    ]
