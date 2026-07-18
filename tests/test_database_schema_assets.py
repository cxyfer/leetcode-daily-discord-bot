import importlib.util
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
INIT_SCHEMA_PATH = DATA_DIR / "init_db_schema.sql"
CLEANUP_SCHEMA_PATH = DATA_DIR / "cleanup_db_schema.sql"
CLEANUP_RUNTIME_PATH = DATA_DIR / "cleanup_runtime_db.py"
TARGET_TABLES = {
    "server_settings",
    "daily_push_settings",
    "llm_translate_results",
    "llm_inspire_results",
}
LEGACY_TABLES = {
    "problems",
    "daily_challenge",
    "problem_embeddings",
    "vec_embeddings",
    "vec_embeddings_chunks",
    "vec_embeddings_info",
    "vec_embeddings_metadatachunks00",
    "vec_embeddings_metadatachunks01",
    "vec_embeddings_metadatatext00",
    "vec_embeddings_metadatatext01",
    "vec_embeddings_rowids",
    "vec_embeddings_vector_chunks00",
}


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_sql_script(db_path: Path, sql: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.executescript(sql)


def _get_user_tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {name for (name,) in rows}


def _get_all_tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {name for (name,) in rows}


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cleanup_runtime_module():
    return _load_module("cleanup_runtime_db", CLEANUP_RUNTIME_PATH)


def test_init_db_schema_sql_creates_only_runtime_tables(tmp_path):
    db_path = tmp_path / "init-schema.sqlite"

    _run_sql_script(db_path, _read_sql(INIT_SCHEMA_PATH))

    assert _get_user_tables(db_path) == TARGET_TABLES


def test_init_db_schema_enforces_daily_push_source_and_identity(tmp_path):
    db_path = tmp_path / "push-constraints.sqlite"
    _run_sql_script(db_path, _read_sql(INIT_SCHEMA_PATH))

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO server_settings (server_id) VALUES (1)")
        for index, source in enumerate(("leetcode.com", "sheep", "0x3f"), start=1):
            connection.execute(
                "INSERT INTO daily_push_settings (server_id, source, channel_id) VALUES (?, ?, ?)",
                (1, source, index),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO daily_push_settings (server_id, source, channel_id) VALUES (1, 'sheep', 99)"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO daily_push_settings (server_id, source, channel_id) VALUES (1, 'unknown', 100)"
            )

        connection.execute("DELETE FROM server_settings WHERE server_id = 1")
        remaining_pushes = connection.execute(
            "SELECT COUNT(*) FROM daily_push_settings WHERE server_id = 1"
        ).fetchone()[0]

    assert remaining_pushes == 0


def test_cleanup_db_schema_sql_removes_legacy_tables_and_is_idempotent(tmp_path):
    db_path = tmp_path / "cleanup-schema.sqlite"

    _run_sql_script(db_path, _read_sql(INIT_SCHEMA_PATH))
    legacy_sql = "\n".join(
        f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT);" for table_name in sorted(LEGACY_TABLES)
    )
    _run_sql_script(db_path, legacy_sql)

    assert TARGET_TABLES.issubset(_get_user_tables(db_path))
    assert LEGACY_TABLES.issubset(_get_user_tables(db_path))

    cleanup_sql = _read_sql(CLEANUP_SCHEMA_PATH)
    _run_sql_script(db_path, cleanup_sql)
    assert _get_user_tables(db_path) == TARGET_TABLES

    _run_sql_script(db_path, cleanup_sql)
    assert _get_user_tables(db_path) == TARGET_TABLES


def test_table_inspection_excludes_sqlite_internal_tables(tmp_path):
    db_path = tmp_path / "sqlite-master-filter.sqlite"

    _run_sql_script(db_path, "CREATE TABLE keeps_me (id INTEGER PRIMARY KEY AUTOINCREMENT);")

    assert "sqlite_sequence" in _get_all_tables(db_path)
    assert _get_user_tables(db_path) == {"keeps_me"}


@pytest.mark.parametrize(
    ("table_name", "legacy_columns", "insert_sql", "expected_row"),
    [
        (
            "llm_translate_results",
            (
                "problem_id TEXT NOT NULL, translation TEXT, created_at INTEGER NOT NULL, "
                "model_name TEXT, domain TEXT NOT NULL, PRIMARY KEY (domain, problem_id)"
            ),
            (
                "INSERT INTO llm_translate_results "
                "(problem_id, translation, created_at, model_name, domain) "
                "VALUES ('two-sum', '翻譯', 1234567890, 'gemini', 'leetcode')"
            ),
            ("leetcode", "two-sum", "zh-TW", "翻譯", 1234567890, "gemini"),
        ),
        (
            "llm_inspire_results",
            (
                "problem_id TEXT NOT NULL, thinking TEXT, traps TEXT, algorithms TEXT, "
                "inspiration TEXT, created_at INTEGER NOT NULL, model_name TEXT, "
                "domain TEXT NOT NULL, PRIMARY KEY (domain, problem_id)"
            ),
            (
                "INSERT INTO llm_inspire_results "
                "(problem_id, thinking, traps, algorithms, inspiration, created_at, model_name, domain) "
                "VALUES ('abc100-a', '思路', '陷阱', 'DP', '靈感', 1234567890, 'gemini', 'atcoder')"
            ),
            ("atcoder", "abc100-a", "zh-TW", "思路", "陷阱", "DP", "靈感", 1234567890, "gemini"),
        ),
    ],
)
def test_cleanup_runtime_db_rebuilds_legacy_llm_tables_with_source_alias(
    tmp_path, cleanup_runtime_module, table_name, legacy_columns, insert_sql, expected_row
):
    db_path = tmp_path / "legacy-runtime.sqlite"
    temp_db_path = tmp_path / "legacy-runtime.cleanup-tmp.sqlite"

    with sqlite3.connect(db_path) as connection:
        connection.execute(f"CREATE TABLE {table_name} ({legacy_columns})")
        connection.execute(insert_sql)
        connection.commit()

    copied_tables = cleanup_runtime_module.rebuild_database(
        db_path,
        INIT_SCHEMA_PATH,
        temp_db_path,
    )

    assert table_name in copied_tables

    with sqlite3.connect(temp_db_path) as connection:
        row = connection.execute(f"SELECT * FROM {table_name}").fetchone()

    assert row == expected_row


def test_cleanup_runtime_db_converts_legacy_server_settings_to_leetcode_push(tmp_path, cleanup_runtime_module):
    db_path = tmp_path / "legacy-settings.sqlite"
    temp_db_path = tmp_path / "legacy-settings.cleanup-tmp.sqlite"

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
        connection.execute(
            """
            INSERT INTO server_settings
                (server_id, channel_id, role_id, post_time, timezone, language)
            VALUES (123, 456, 789, '08:30', 'Asia/Taipei', 'en-US')
            """
        )

    copied_tables = cleanup_runtime_module.rebuild_database(
        db_path,
        INIT_SCHEMA_PATH,
        temp_db_path,
    )

    assert "server_settings" in copied_tables
    assert "daily_push_settings" in copied_tables
    with sqlite3.connect(temp_db_path) as connection:
        guild_row = connection.execute("SELECT server_id, language FROM server_settings").fetchone()
        push_row = connection.execute(
            """
            SELECT server_id, source, channel_id, role_id, post_time, timezone
            FROM daily_push_settings
            """
        ).fetchone()

    assert guild_row == (123, "en-US")
    assert push_row == (123, "leetcode.com", 456, 789, "08:30", "Asia/Taipei")
