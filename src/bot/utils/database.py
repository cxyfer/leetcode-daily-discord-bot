import json
import logging
import os
import sqlite3
import time
from pathlib import Path

from .paths import get_repo_root, resolve_repo_path

# Module-level logger
logger = logging.getLogger("database")
REPO_ROOT = get_repo_root()


def resolve_db_path(db_path: str | Path) -> str:
    return str(resolve_repo_path(db_path, REPO_ROOT))


class SettingsDatabaseManager:
    """
    This class manages server settings in the database.
    """

    def __init__(self, db_path="data/settings.db"):
        """
        Initialize the database manager

        Args:
            db_path (str): The path to the database file
        """

        self.db_path = resolve_db_path(db_path)
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Database manager initialized with database at {self.db_path}")

    def _init_db(self):
        """Initialize the database, create necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create server settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            role_id INTEGER,
            post_time TEXT DEFAULT '00:00',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()
        logger.debug("Database tables initialized")

    def get_server_settings(self, server_id):
        """Get the settings for a specific server

        Args:
            server_id (int): Discord server ID

            Returns:
                dict: server settings, return None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT channel_id, role_id, post_time, timezone FROM server_settings WHERE server_id = ?",
            (server_id,),
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            logger.debug(f"Server {server_id} settings: {result}")
            return {
                "server_id": server_id,
                "channel_id": result[0],
                "role_id": result[1],
                "post_time": result[2],
                "timezone": result[3],
            }
        return None

    def set_server_settings(self, server_id, channel_id, role_id=None, post_time="00:00", timezone="UTC"):
        """Set or update server settings

        Args:
            server_id (int): Discord server ID
            channel_id (int): The channel ID to send the daily challenge
            role_id (int, optional): The role ID to mention
            post_time (str, optional): The time to send the daily challenge, format "HH:MM"
            timezone (str, optional): The timezone name

        Returns:
            bool: return True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO server_settings (server_id, channel_id, role_id, post_time, timezone)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(server_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    role_id = excluded.role_id,
                    post_time = excluded.post_time,
                    timezone = excluded.timezone,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (server_id, channel_id, role_id, post_time, timezone),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting server settings: {e}")
            return False
        finally:
            logger.debug(f"Server {server_id} settings updated: ({channel_id}, {role_id}, {post_time}, {timezone})")
            conn.close()

    def get_all_servers(self):
        """Get all servers with settings

        Returns:
            list: A list of dictionaries containing all server settings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT server_id, channel_id, role_id, post_time, timezone FROM server_settings")
        results = cursor.fetchall()
        conn.close()

        servers = []
        for row in results:
            servers.append(
                {
                    "server_id": row[0],
                    "channel_id": row[1],
                    "role_id": row[2],
                    "post_time": row[3],
                    "timezone": row[4],
                }
            )

        return servers

    def delete_server_settings(self, server_id):
        """Delete server settings

        Args:
            server_id (int): Discord server ID

        Returns:
            bool: return True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM server_settings WHERE server_id = ?", (server_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting server settings: {e}")
            return False
        finally:
            conn.close()


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
            translation TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (source, problem_id)
        )
        """)
        conn.commit()
        conn.close()

    def get_translation(self, source, problem_id, expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translation, created_at, model_name FROM llm_translate_results WHERE source = ? AND problem_id = ?",
            (source, problem_id),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            translation, created_at, model_name = row
            if int(time.time()) - created_at <= expire_seconds:
                return {"translation": translation, "model_name": model_name}
        return None

    def save_translation(self, source, problem_id, translation, model_name=None):
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
            "(source, problem_id, translation, created_at, model_name) VALUES (?, ?, ?, ?, ?)",
            (source, problem_id, translation, now, model_name),
        )
        conn.commit()
        conn.close()
        logger.info(f"Saved LLM translation for {source}/{problem_id}, model={model_name}")


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
            thinking TEXT,
            traps TEXT,
            algorithms TEXT,
            inspiration TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (source, problem_id)
        )
        """)
        conn.commit()
        conn.close()

    def get_inspire(self, source, problem_id, expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thinking, traps, algorithms, inspiration, created_at, model_name "
            "FROM llm_inspire_results WHERE source = ? AND problem_id = ?",
            (source, problem_id),
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

    def save_inspire(self, source, problem_id, thinking, traps, algorithms, inspiration, model_name=None):
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
            "(source, problem_id, thinking, traps, algorithms, inspiration, created_at, model_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source,
                problem_id,
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
        logger.info(f"Saved LLM inspire for {source}/{problem_id}, model={model_name}")


if __name__ == "__main__":
    # Example usage
    db_manager = SettingsDatabaseManager()
    db_manager.set_server_settings(123456789, 987654321, role_id=111222333, post_time="12:00", timezone="UTC")
    settings = db_manager.get_server_settings(123456789)
    logger.debug(settings)
    db_manager.delete_server_settings(123456789)  # Delete settings for server ID 123456789
