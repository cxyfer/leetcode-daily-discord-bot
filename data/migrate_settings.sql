-- Migration script: Move server_settings from settings.db to data.db
-- Usage: sqlite3 data/data.db < migrate_settings.sql

-- Create server_settings table in data.db if it doesn't exist
CREATE TABLE IF NOT EXISTS server_settings (
    server_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    role_id INTEGER,
    post_time TEXT DEFAULT '00:00',
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attach the old settings.db database
ATTACH DATABASE 'data/settings.db' AS old_db;

-- Copy data from old database to new database
-- Use INSERT OR REPLACE to handle any potential conflicts
INSERT OR REPLACE INTO server_settings (
    server_id, 
    channel_id, 
    role_id, 
    post_time, 
    timezone, 
    created_at, 
    updated_at
)
SELECT 
    server_id, 
    channel_id, 
    role_id, 
    post_time, 
    timezone, 
    created_at, 
    updated_at
FROM old_db.server_settings;

-- Detach the old database
DETACH DATABASE old_db;

-- Show migration results
SELECT 'Migration completed. Total records:' as status, COUNT(*) as count FROM server_settings;