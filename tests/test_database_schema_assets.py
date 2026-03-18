import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
INIT_SCHEMA_PATH = DATA_DIR / "init_db_schema.sql"
CLEANUP_SCHEMA_PATH = DATA_DIR / "cleanup_db_schema.sql"
TARGET_TABLES = {
    "server_settings",
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


def test_init_db_schema_sql_creates_only_runtime_tables(tmp_path):
    db_path = tmp_path / "init-schema.sqlite"

    _run_sql_script(db_path, _read_sql(INIT_SCHEMA_PATH))

    assert _get_user_tables(db_path) == TARGET_TABLES



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
