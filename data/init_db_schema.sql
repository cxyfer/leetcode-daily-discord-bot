-- Manual initialization for the runtime SQLite schema.
-- Run this manually only while the bot is stopped.

CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'zh-TW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
);

CREATE TABLE IF NOT EXISTS llm_translate_results (
    source TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'zh-TW',
    translation TEXT,
    created_at INTEGER NOT NULL,
    model_name TEXT,
    PRIMARY KEY (source, problem_id, locale)
);

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
);
