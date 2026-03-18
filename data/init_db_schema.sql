-- Manual initialization for the runtime SQLite schema.
-- Run this manually only while the bot is stopped.

CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    role_id INTEGER,
    post_time TEXT DEFAULT '00:00',
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS llm_translate_results (
    source TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    translation TEXT,
    created_at INTEGER NOT NULL,
    model_name TEXT,
    PRIMARY KEY (source, problem_id)
);

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
);
