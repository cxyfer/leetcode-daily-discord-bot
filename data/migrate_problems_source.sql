.bail on

-- Migration script: Update problems table to support multi-source
-- Usage: sqlite3 data/data.db < data/migrate_problems_source.sql
-- Please back up the database before running this script.
--
-- IDEMPOTENT: Running this script multiple times is safe.
-- If already migrated, the script will fail early with "duplicate column name: source".

PRAGMA foreign_keys = OFF;

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

-- Add source column. This will fail if already migrated (idempotent guard).
-- With .bail on, script stops here on re-run.
ALTER TABLE problems ADD COLUMN source TEXT NOT NULL DEFAULT 'leetcode';

BEGIN TRANSACTION;

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
