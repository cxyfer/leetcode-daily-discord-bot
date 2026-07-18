import sqlite3
from pathlib import Path

import pytest

from bot.utils.database import SettingsDatabaseManager


def _create_legacy_database(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE server_settings (
                server_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                role_id INTEGER,
                post_time TEXT DEFAULT '00:00',
                timezone TEXT DEFAULT 'UTC',
                language TEXT NOT NULL DEFAULT 'zh-TW',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO server_settings
                (server_id, channel_id, role_id, post_time, timezone, language)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 101, 201, "08:00", "Asia/Taipei", "zh-TW"),
                (2, 102, None, "09:30", "UTC+8", "en-US"),
            ],
        )


def _table_columns(db_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute(f'PRAGMA table_info("{table_name}")')}


def test_daily_push_crud_is_independent_per_source(tmp_path):
    manager = SettingsDatabaseManager(tmp_path / "settings.sqlite")

    assert manager.set_daily_push(1, "leetcode.com", 101, 201, "08:00", "Asia/Taipei")
    assert manager.set_daily_push(1, "sheep", 102, None, "09:00", "UTC")
    assert manager.set_daily_push(1, "0x3f", 103, 203, "10:00", "UTC+8")
    assert manager.set_daily_push(1, "sheep", 202, 302, "11:00", "Asia/Tokyo")

    pushes = manager.get_daily_pushes(1)

    assert [push["source"] for push in pushes] == ["leetcode.com", "sheep", "0x3f"]
    assert manager.get_daily_push(1, "leetcode.com")["channel_id"] == 101
    assert manager.get_daily_push(1, "0x3f")["channel_id"] == 103
    assert manager.get_daily_push(1, "sheep") == {
        "server_id": 1,
        "source": "sheep",
        "channel_id": 202,
        "role_id": 302,
        "post_time": "11:00",
        "timezone": "Asia/Tokyo",
    }


def test_daily_push_creation_ensures_default_guild_language(tmp_path):
    manager = SettingsDatabaseManager(tmp_path / "settings.sqlite")

    assert manager.set_daily_push(7, "sheep", 700)

    assert manager.get_server_settings(7) == {"server_id": 7, "language": "zh-TW"}
    assert manager.set_server_language(7, "en-US")
    assert manager.get_server_settings(7) == {"server_id": 7, "language": "en-US"}
    assert manager.get_daily_push(7, "sheep")["channel_id"] == 700


def test_daily_push_rejects_unsupported_source(tmp_path):
    manager = SettingsDatabaseManager(tmp_path / "settings.sqlite")

    with pytest.raises(ValueError, match="Unsupported daily push source"):
        manager.set_daily_push(1, "unknown", 100)


def test_delete_daily_push_and_server_reset_are_scoped(tmp_path):
    manager = SettingsDatabaseManager(tmp_path / "settings.sqlite")
    manager.set_daily_push(1, "leetcode.com", 101)
    manager.set_daily_push(1, "sheep", 102)

    assert manager.delete_daily_push(1, "sheep")
    assert manager.get_daily_push(1, "sheep") is None
    assert manager.get_daily_push(1, "leetcode.com") is not None
    assert manager.get_server_settings(1) is not None

    assert manager.delete_server_settings(1)
    assert manager.get_server_settings(1) is None
    assert manager.get_daily_pushes(1) == []


def test_get_all_daily_pushes_includes_joined_language(tmp_path):
    manager = SettingsDatabaseManager(tmp_path / "settings.sqlite")
    manager.set_server_language(1, "en-US")
    manager.set_daily_push(1, "leetcode.com", 101)
    manager.set_daily_push(2, "sheep", 202)

    assert manager.get_all_daily_pushes() == [
        {
            "server_id": 1,
            "source": "leetcode.com",
            "channel_id": 101,
            "role_id": None,
            "post_time": "00:00",
            "timezone": "UTC",
            "language": "en-US",
        },
        {
            "server_id": 2,
            "source": "sheep",
            "channel_id": 202,
            "role_id": None,
            "post_time": "00:00",
            "timezone": "UTC",
            "language": "zh-TW",
        },
    ]


def test_legacy_database_is_backed_up_and_migrated(tmp_path):
    db_path = tmp_path / "legacy.sqlite"
    _create_legacy_database(db_path)

    manager = SettingsDatabaseManager(db_path)

    backups = list(tmp_path.glob("legacy.sqlite.*.pre-push-redesign.bak"))
    assert len(backups) == 1
    assert _table_columns(db_path, "server_settings") == {
        "server_id",
        "language",
        "created_at",
        "updated_at",
    }
    assert "daily_push_settings" in {
        row[0] for row in sqlite3.connect(db_path).execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert manager.get_server_settings(2) == {"server_id": 2, "language": "en-US"}
    assert manager.get_daily_push(1, "leetcode.com") == {
        "server_id": 1,
        "source": "leetcode.com",
        "channel_id": 101,
        "role_id": 201,
        "post_time": "08:00",
        "timezone": "Asia/Taipei",
    }
    assert manager.get_daily_push(2, "leetcode.com")["channel_id"] == 102

    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT COUNT(*) FROM server_settings").fetchone()[0] == 2
        assert "channel_id" in {row[1] for row in backup.execute("PRAGMA table_info(server_settings)")}


def test_normalized_database_startup_is_idempotent(tmp_path):
    db_path = tmp_path / "settings.sqlite"
    manager = SettingsDatabaseManager(db_path)
    manager.set_daily_push(1, "sheep", 101)

    SettingsDatabaseManager(db_path)

    assert list(tmp_path.glob("settings.sqlite.*.pre-push-redesign.bak")) == []
    assert manager.get_daily_push(1, "sheep")["channel_id"] == 101


def test_legacy_migration_validation_failure_rolls_back(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.sqlite"
    _create_legacy_database(db_path)

    def fail_validation(self, connection, expected_count):
        raise RuntimeError("injected migration validation failure")

    monkeypatch.setattr(SettingsDatabaseManager, "_validate_legacy_migration", fail_validation)

    with pytest.raises(RuntimeError, match="injected migration validation failure"):
        SettingsDatabaseManager(db_path)

    assert "channel_id" in _table_columns(db_path, "server_settings")
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM server_settings").fetchone()[0] == 2
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'daily_push_settings'"
            ).fetchone()
            is None
        )
    assert len(list(tmp_path.glob("legacy.sqlite.*.pre-push-redesign.bak"))) == 1
