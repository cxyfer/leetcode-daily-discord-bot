#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = DATA_DIR / "data.db"
DEFAULT_INIT_SCRIPT_PATH = DATA_DIR / "init_db_schema.sql"
PRESERVED_TABLES = (
    "server_settings",
    "llm_translate_results",
    "llm_inspire_results",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild an existing runtime SQLite database so it only keeps the currently supported runtime tables."
        )
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Database file to clean up (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--init-script-path",
        type=Path,
        default=DEFAULT_INIT_SCRIPT_PATH,
        help=f"Runtime schema SQL to apply to the rebuilt database (default: {DEFAULT_INIT_SCRIPT_PATH})",
    )
    parser.add_argument(
        "--backup-path",
        type=Path,
        default=None,
        help="Optional backup destination. Defaults to <db>.YYYYMMDD-HHMMSS.bak",
    )
    parser.add_argument(
        "--skip-vacuum",
        action="store_true",
        help="Skip VACUUM after rebuilding the compact runtime database.",
    )
    return parser.parse_args()


def build_backup_path(db_path: Path, backup_path: Path | None) -> Path:
    if backup_path is not None:
        return backup_path

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return db_path.with_name(f"{db_path.name}.{timestamp}.bak")


def build_temp_db_path(db_path: Path) -> Path:
    return db_path.with_name(f"{db_path.stem}.cleanup-tmp{db_path.suffix}")


def validate_paths(db_path: Path, init_script_path: Path, backup_path: Path, temp_db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"Database file not found: {db_path}")
    if not init_script_path.exists():
        raise SystemExit(f"Init SQL file not found: {init_script_path}")
    if backup_path.exists():
        raise SystemExit(f"Backup path already exists: {backup_path}")
    if temp_db_path.exists():
        raise SystemExit(f"Temporary database path already exists: {temp_db_path}")


def table_exists(conn: sqlite3.Connection, schema: str, table_name: str) -> bool:
    row = conn.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_table_columns(conn: sqlite3.Connection, schema: str, table_name: str) -> list[str]:
    rows = conn.execute(f'PRAGMA {schema}.table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def rebuild_database(db_path: Path, init_script_path: Path, temp_db_path: Path) -> list[str]:
    init_sql = init_script_path.read_text(encoding="utf-8")
    copied_tables: list[str] = []

    with sqlite3.connect(temp_db_path) as conn:
        conn.executescript(init_sql)
        conn.execute("ATTACH DATABASE ? AS old", (str(db_path),))

        for table_name in PRESERVED_TABLES:
            if not table_exists(conn, "old", table_name):
                continue

            destination_columns = get_table_columns(conn, "main", table_name)
            source_columns = set(get_table_columns(conn, "old", table_name))
            column_names = [column for column in destination_columns if column in source_columns]

            if not column_names:
                continue

            quoted_columns = ", ".join(quote_ident(column) for column in column_names)
            conn.execute(
                f"INSERT INTO main.{quote_ident(table_name)} ({quoted_columns}) "
                f"SELECT {quoted_columns} FROM old.{quote_ident(table_name)}"
            )
            copied_tables.append(table_name)

    return copied_tables


def vacuum(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("VACUUM;")


def main() -> None:
    args = parse_args()
    db_path = args.db_path.expanduser().resolve()
    init_script_path = args.init_script_path.expanduser().resolve()
    backup_path = build_backup_path(db_path, args.backup_path)
    temp_db_path = build_temp_db_path(db_path)

    validate_paths(db_path, init_script_path, backup_path, temp_db_path)

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")

    copied_tables = rebuild_database(db_path, init_script_path, temp_db_path)
    temp_db_path.replace(db_path)
    print(f"Rebuilt runtime database: {db_path}")

    if copied_tables:
        print("Copied tables: " + ", ".join(copied_tables))
    else:
        print("Copied tables: none")

    if args.skip_vacuum:
        print("VACUUM skipped.")
        return

    vacuum(db_path)
    print(f"VACUUM completed: {db_path}")


if __name__ == "__main__":
    main()
