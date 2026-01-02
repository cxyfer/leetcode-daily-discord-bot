.bail on

-- Migration script: Update problems table to support multi-source
-- Usage: sqlite3 data/data.db < data/migrate_problems_source.sql
-- Please back up the database before running this script.

-- Pre-check: if source already exists, stop to avoid a destructive re-run.
CREATE TEMP TABLE IF NOT EXISTS _migration_guard (
    needs_migration INTEGER NOT NULL CHECK (needs_migration = 1)
);
DELETE FROM _migration_guard;
INSERT INTO _migration_guard (needs_migration)
SELECT CASE
    WHEN EXISTS (
        SELECT 1
        FROM pragma_table_info('problems')
        WHERE name = 'source'
    )
    THEN 0
    ELSE 1
END;
DROP TABLE _migration_guard;

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- Ensure the old schema exists (safe for fresh environments).
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL,
    title TEXT,
    title_cn TEXT,
    difficulty TEXT,
    ac_rate REAL,
    rating REAL,
    contest TEXT,
    problem_index TEXT,
    tags TEXT,
    link TEXT,
    category TEXT,
    paid_only INTEGER,
    content TEXT,
    content_cn TEXT,
    similar_questions TEXT
);

-- Ensure source column exists for data migration.
ALTER TABLE problems
    ADD COLUMN source TEXT NOT NULL DEFAULT 'leetcode';

DROP TABLE IF EXISTS problems_old;
ALTER TABLE problems RENAME TO problems_old;

-- New schema: composite primary key (source, id).
CREATE TABLE IF NOT EXISTS problems (
    id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'leetcode',
    slug TEXT NOT NULL,
    title TEXT,
    title_cn TEXT,
    difficulty TEXT,
    ac_rate REAL,
    rating REAL,
    contest TEXT,
    problem_index TEXT,
    tags TEXT,
    link TEXT,
    category TEXT,
    paid_only INTEGER,
    content TEXT,
    content_cn TEXT,
    similar_questions TEXT,
    PRIMARY KEY (source, id)
);

INSERT OR REPLACE INTO problems (
    id,
    source,
    slug,
    title,
    title_cn,
    difficulty,
    ac_rate,
    rating,
    contest,
    problem_index,
    tags,
    link,
    category,
    paid_only,
    content,
    content_cn,
    similar_questions
)
SELECT
    CAST(id AS TEXT) AS id,
    source,
    slug,
    title,
    title_cn,
    difficulty,
    ac_rate,
    rating,
    contest,
    problem_index,
    tags,
    link,
    category,
    paid_only,
    content,
    content_cn,
    similar_questions
FROM problems_old;

DROP TABLE IF EXISTS problems_old;

COMMIT;
PRAGMA foreign_keys = ON;

SELECT 'Migration completed. Total records:' as status, COUNT(*) as count FROM problems;
