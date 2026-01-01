-- Migration script: create embedding metadata table
-- Usage: sqlite3 data/data.db < data/migrate_embeddings.sql

CREATE TABLE IF NOT EXISTS problem_embeddings (
    source TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    rewritten_content TEXT,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source, problem_id)
);

SELECT 'Migration completed. Total records:' as status, COUNT(*) as count FROM problem_embeddings;
