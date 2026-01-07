"""
Unit tests for get_daily_history helper.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

import leetcode
from leetcode import LeetCodeClient


@pytest_asyncio.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
    client = LeetCodeClient(domain="com", db_path=str(db_path))
    yield client
    await client.shutdown()


@pytest.mark.asyncio
async def test_get_daily_history_handles_failures_and_order(client, monkeypatch):
    monkeypatch.setattr(
        leetcode,
        "generate_history_dates",
        lambda anchor_date, years=5: ["2025-01-07", "2024-01-07", "2023-01-07"],
    )

    async def fake_get_daily_challenge(date_str, domain=None):
        if date_str == "2024-01-07":
            raise ValueError("boom")
        return {
            "date": date_str,
            "id": 1,
            "title": "Test",
            "difficulty": "Easy",
            "link": f"https://leetcode.com/{date_str}",
            "rating": 1234 if date_str == "2025-01-07" else None,
        }

    client.get_daily_challenge = AsyncMock(side_effect=fake_get_daily_challenge)

    result = await client.get_daily_history("2026-01-07")

    assert result == [
        {
            "date": "2025-01-07",
            "id": 1,
            "title": "Test",
            "difficulty": "Easy",
            "link": "https://leetcode.com/2025-01-07",
            "rating": 1234,
        },
        {
            "date": "2023-01-07",
            "id": 1,
            "title": "Test",
            "difficulty": "Easy",
            "link": "https://leetcode.com/2023-01-07",
        },
    ]
