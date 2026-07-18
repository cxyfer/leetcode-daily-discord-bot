import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .daily_sources import DEFAULT_DAILY_PUSH_SOURCE, validate_daily_push_source
from .paths import get_repo_root, resolve_repo_path

# Module-level logger
logger = logging.getLogger("database")
REPO_ROOT = get_repo_root()

SERVER_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'zh-TW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

DAILY_PUSH_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_push_settings (
    server_id INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('leetcode.com', 'sheep', '0x3f')),
    channel_id INTEGER NOT NULL,
    role_id INTEGER,
    post_time TEXT NOT NULL DEFAULT '00:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, source),
    FOREIGN KEY (server_id) REFERENCES server_settings(server_id) ON DELETE CASCADE
)
"""


def resolve_db_path(db_path: str | Path) -> str:
    return str(resolve_repo_path(db_path, REPO_ROOT))


class SettingsDatabaseManager:
    """Manage guild-wide language and source-specific daily push settings."""

    def __init__(self, db_path="data/data.db"):
        self.db_path = resolve_db_path(db_path)
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Database manager initialized with database at {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            is not None
        )

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in connection.execute(f'PRAGMA table_info("{table_name}")')}

    def _has_legacy_server_settings(self, connection: sqlite3.Connection) -> bool:
        if not self._table_exists(connection, "server_settings"):
            return False
        columns = self._table_columns(connection, "server_settings")
        return bool({"channel_id", "role_id", "post_time", "timezone"} & columns)

    @staticmethod
    def _create_settings_tables(connection: sqlite3.Connection) -> None:
        connection.execute(SERVER_SETTINGS_SCHEMA)
        connection.execute(DAILY_PUSH_SETTINGS_SCHEMA)

    def _create_migration_backup(self, connection: sqlite3.Connection) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = Path(f"{self.db_path}.{timestamp}.pre-push-redesign.bak")
        with sqlite3.connect(backup_path) as backup_connection:
            connection.backup(backup_connection)
        logger.info("Created pre-migration database backup at %s", backup_path)
        return backup_path

    def _validate_legacy_migration(self, connection: sqlite3.Connection, expected_count: int) -> None:
        guild_count = connection.execute("SELECT COUNT(*) FROM server_settings").fetchone()[0]
        push_count = connection.execute(
            "SELECT COUNT(*) FROM daily_push_settings WHERE source = ?",
            (DEFAULT_DAILY_PUSH_SOURCE,),
        ).fetchone()[0]
        missing_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM legacy_server_settings AS legacy
            LEFT JOIN server_settings AS guild ON guild.server_id = legacy.server_id
            LEFT JOIN daily_push_settings AS push
                ON push.server_id = legacy.server_id AND push.source = ?
            WHERE guild.server_id IS NULL OR push.server_id IS NULL
            """,
            (DEFAULT_DAILY_PUSH_SOURCE,),
        ).fetchone()[0]
        if guild_count != expected_count or push_count != expected_count or missing_count:
            raise RuntimeError(
                "Legacy settings migration validation failed: "
                f"expected={expected_count}, guilds={guild_count}, pushes={push_count}, missing={missing_count}"
            )

    def _migrate_legacy_server_settings(self, connection: sqlite3.Connection) -> None:
        legacy_columns = self._table_columns(connection, "server_settings")
        legacy_count = connection.execute("SELECT COUNT(*) FROM server_settings").fetchone()[0]

        def column_or_default(column: str, default_sql: str) -> str:
            return f'COALESCE("{column}", {default_sql})' if column in legacy_columns else default_sql

        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("ALTER TABLE server_settings RENAME TO legacy_server_settings")
            self._create_settings_tables(connection)
            connection.execute(
                f"""
                INSERT INTO server_settings (server_id, language, created_at, updated_at)
                SELECT
                    server_id,
                    {column_or_default("language", "'zh-TW'")},
                    {column_or_default("created_at", "CURRENT_TIMESTAMP")},
                    {column_or_default("updated_at", "CURRENT_TIMESTAMP")}
                FROM legacy_server_settings
                """
            )
            connection.execute(
                f"""
                INSERT INTO daily_push_settings
                    (server_id, source, channel_id, role_id, post_time, timezone, created_at, updated_at)
                SELECT
                    server_id,
                    ?,
                    channel_id,
                    {column_or_default("role_id", "NULL")},
                    {column_or_default("post_time", "'00:00'")},
                    {column_or_default("timezone", "'UTC'")},
                    {column_or_default("created_at", "CURRENT_TIMESTAMP")},
                    {column_or_default("updated_at", "CURRENT_TIMESTAMP")}
                FROM legacy_server_settings
                """,
                (DEFAULT_DAILY_PUSH_SOURCE,),
            )
            self._validate_legacy_migration(connection, legacy_count)
            connection.execute("DROP TABLE legacy_server_settings")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        logger.info("Migrated %s legacy server settings rows to normalized daily pushes", legacy_count)

    def _init_db(self) -> None:
        with self._connect() as connection:
            if self._has_legacy_server_settings(connection):
                self._create_migration_backup(connection)
                self._migrate_legacy_server_settings(connection)
            else:
                self._create_settings_tables(connection)
        logger.debug("Database tables initialized")

    def get_server_settings(self, server_id):
        """Get the settings for a specific server

        Args:
            server_id (int): Discord server ID

            Returns:
                dict: server settings, return None if not found
        """
        with self._connect() as connection:
            result = connection.execute(
                "SELECT language FROM server_settings WHERE server_id = ?",
                (server_id,),
            ).fetchone()
        if result:
            return {"server_id": server_id, "language": result[0]}
        return None

    def set_server_language(self, server_id: int, language: str = "zh-TW") -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO server_settings (server_id, language)
                    VALUES (?, ?)
                    ON CONFLICT(server_id) DO UPDATE SET
                        language = excluded.language,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (server_id, language),
                )
            return True
        except sqlite3.Error as exc:
            logger.error("Error setting server language: %s", exc)
            return False

    @staticmethod
    def _push_from_row(row: tuple) -> dict:
        return {
            "server_id": row[0],
            "source": row[1],
            "channel_id": row[2],
            "role_id": row[3],
            "post_time": row[4],
            "timezone": row[5],
        }

    def get_daily_push(self, server_id: int, source: str) -> dict | None:
        validate_daily_push_source(source)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT server_id, source, channel_id, role_id, post_time, timezone
                FROM daily_push_settings
                WHERE server_id = ? AND source = ?
                """,
                (server_id, source),
            ).fetchone()
        return self._push_from_row(row) if row else None

    def get_daily_pushes(self, server_id: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT server_id, source, channel_id, role_id, post_time, timezone
                FROM daily_push_settings
                WHERE server_id = ?
                ORDER BY CASE source WHEN 'leetcode.com' THEN 1 WHEN 'sheep' THEN 2 WHEN '0x3f' THEN 3 END
                """,
                (server_id,),
            ).fetchall()
        return [self._push_from_row(row) for row in rows]

    def get_all_daily_pushes(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    push.server_id, push.source, push.channel_id, push.role_id,
                    push.post_time, push.timezone, guild.language
                FROM daily_push_settings AS push
                JOIN server_settings AS guild ON guild.server_id = push.server_id
                ORDER BY push.server_id,
                    CASE push.source WHEN 'leetcode.com' THEN 1 WHEN 'sheep' THEN 2 WHEN '0x3f' THEN 3 END
                """
            ).fetchall()
        pushes = []
        for row in rows:
            push = self._push_from_row(row[:6])
            push["language"] = row[6]
            pushes.append(push)
        return pushes

    def set_daily_push(
        self,
        server_id: int,
        source: str,
        channel_id: int,
        role_id: int | None = None,
        post_time: str = "00:00",
        timezone: str = "UTC",
    ) -> bool:
        validate_daily_push_source(source)
        try:
            with self._connect() as connection:
                connection.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (server_id,))
                connection.execute(
                    """
                    INSERT INTO daily_push_settings
                        (server_id, source, channel_id, role_id, post_time, timezone)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(server_id, source) DO UPDATE SET
                        channel_id = excluded.channel_id,
                        role_id = excluded.role_id,
                        post_time = excluded.post_time,
                        timezone = excluded.timezone,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (server_id, source, channel_id, role_id, post_time, timezone),
                )
            return True
        except sqlite3.Error as exc:
            logger.error("Error setting daily push: %s", exc)
            return False

    def delete_daily_push(self, server_id: int, source: str) -> bool:
        validate_daily_push_source(source)
        try:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM daily_push_settings WHERE server_id = ? AND source = ?",
                    (server_id, source),
                )
            return True
        except sqlite3.Error as exc:
            logger.error("Error deleting daily push: %s", exc)
            return False

    def delete_server_settings(self, server_id):
        """Delete server settings

        Args:
            server_id (int): Discord server ID

        Returns:
            bool: return True if deleted successfully
        """
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM server_settings WHERE server_id = ?", (server_id,))
            return True
        except sqlite3.Error as exc:
            logger.error("Error deleting server settings: %s", exc)
            return False


class LLMTranslateDatabaseManager:
    def __init__(self, db_path="data/data.db", expire_seconds=604800):
        self.db_path = resolve_db_path(db_path)
        self.expire_seconds = expire_seconds
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"LLMTranslate DB manager initialized with database at {self.db_path}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Migrate: drop legacy table with (problem_id INTEGER, domain TEXT) PK
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='llm_translate_results'")
        row = cursor.fetchone()
        if row and "domain" in row[0]:
            cursor.execute("DROP TABLE llm_translate_results")
            logger.info("Dropped legacy llm_translate_results table (old schema)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_translate_results (
            source TEXT NOT NULL,
            problem_id TEXT NOT NULL,
            locale TEXT NOT NULL DEFAULT 'zh-TW',
            translation TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (source, problem_id, locale)
        )
        """)
        # Migrate: add locale column if missing (for existing databases)
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(llm_translate_results)").fetchall()}
        if "locale" not in columns:
            cursor.execute("DROP TABLE llm_translate_results")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_translate_results (
                source TEXT NOT NULL,
                problem_id TEXT NOT NULL,
                locale TEXT NOT NULL DEFAULT 'zh-TW',
                translation TEXT,
                created_at INTEGER NOT NULL,
                model_name TEXT,
                PRIMARY KEY (source, problem_id, locale)
            )
            """)
            logger.info("Rebuilt llm_translate_results with locale in PK")
        conn.commit()
        conn.close()

    def get_translation(self, source, problem_id, locale="zh-TW", expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translation, created_at, model_name FROM llm_translate_results "
            "WHERE source = ? AND problem_id = ? AND locale = ?",
            (source, problem_id, locale),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            translation, created_at, model_name = row
            if int(time.time()) - created_at <= expire_seconds:
                return {"translation": translation, "model_name": model_name}
        return None

    def save_translation(self, source, problem_id, translation, locale="zh-TW", model_name=None):
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if translation is None:
            translation = ""
        elif isinstance(translation, (dict, list)):
            translation = json.dumps(translation, ensure_ascii=False)
        else:
            translation = str(translation)
        cursor.execute(
            "INSERT OR REPLACE INTO llm_translate_results "
            "(source, problem_id, locale, translation, created_at, model_name) VALUES (?, ?, ?, ?, ?, ?)",
            (source, problem_id, locale, translation, now, model_name),
        )
        conn.commit()
        conn.close()
        logger.info(f"Saved LLM translation for {source}/{problem_id}/{locale}, model={model_name}")


class LLMInspireDatabaseManager:
    def __init__(self, db_path="data/data.db", expire_seconds=604800):
        self.db_path = resolve_db_path(db_path)
        self.expire_seconds = expire_seconds
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"LLMInspire DB manager initialized with database at {self.db_path}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Migrate: drop legacy table with (problem_id INTEGER, domain TEXT) PK
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='llm_inspire_results'")
        row = cursor.fetchone()
        if row and "domain" in row[0]:
            cursor.execute("DROP TABLE llm_inspire_results")
            logger.info("Dropped legacy llm_inspire_results table (old schema)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_inspire_results (
            source TEXT NOT NULL,
            problem_id TEXT NOT NULL,
            locale TEXT NOT NULL DEFAULT 'zh-TW',
            thinking TEXT,
            traps TEXT,
            algorithms TEXT,
            inspiration TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (source, problem_id, locale)
        )
        """)
        # Migrate: add locale column if missing (for existing databases)
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(llm_inspire_results)").fetchall()}
        if "locale" not in columns:
            cursor.execute("DROP TABLE llm_inspire_results")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_inspire_results (
                source TEXT NOT NULL,
                problem_id TEXT NOT NULL,
                locale TEXT NOT NULL DEFAULT 'zh-TW',
                thinking TEXT,
                traps TEXT,
                algorithms TEXT,
                inspiration TEXT,
                created_at INTEGER NOT NULL,
                model_name TEXT,
                PRIMARY KEY (source, problem_id, locale)
            )
            """)
            logger.info("Rebuilt llm_inspire_results with locale in PK")
        conn.commit()
        conn.close()

    def get_inspire(self, source, problem_id, locale="zh-TW", expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thinking, traps, algorithms, inspiration, created_at, model_name "
            "FROM llm_inspire_results WHERE source = ? AND problem_id = ? AND locale = ?",
            (source, problem_id, locale),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            thinking, traps, algorithms, inspiration, created_at, model_name = row
            if int(time.time()) - created_at <= expire_seconds:
                return {
                    "thinking": thinking,
                    "traps": traps,
                    "algorithms": algorithms,
                    "inspiration": inspiration,
                    "model_name": model_name,
                }
        return None

    def save_inspire(
        self, source, problem_id, thinking, traps, algorithms, inspiration, locale="zh-TW", model_name=None
    ):
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        def safe_str(val):
            if val is None:
                return ""
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)

        cursor.execute(
            "INSERT OR REPLACE INTO llm_inspire_results "
            "(source, problem_id, locale, thinking, traps, algorithms, inspiration, created_at, model_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source,
                problem_id,
                locale,
                safe_str(thinking),
                safe_str(traps),
                safe_str(algorithms),
                safe_str(inspiration),
                now,
                model_name,
            ),
        )
        conn.commit()
        conn.close()
        logger.info(f"Saved LLM inspire for {source}/{problem_id}/{locale}, model={model_name}")


if __name__ == "__main__":
    # Example usage
    db_manager = SettingsDatabaseManager()
    db_manager.set_server_settings(123456789, 987654321, role_id=111222333, post_time="12:00", timezone="UTC")
    settings = db_manager.get_server_settings(123456789)
    logger.debug(settings)
    db_manager.delete_server_settings(123456789)  # Delete settings for server ID 123456789
