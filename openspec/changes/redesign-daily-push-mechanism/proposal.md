## Why

The bot currently stores one notification channel, role, post time, and timezone directly on `server_settings`, so each Discord server can own only one scheduled LeetCode delivery. The upstream daily endpoint now exposes `sheep` and `0x3f` as additional daily sources, both of which may return multiple problems. Server administrators need to schedule those sources independently without duplicating guild-wide settings or losing existing LeetCode schedules.

## What Changes

- Separate guild-wide settings from source-specific daily push settings.
- Allow each server to configure at most one push for each supported source: `leetcode.com`, `sheep`, and `0x3f`.
- Keep channel, role, post time, and timezone independent for each source while keeping language shared by the guild.
- Extend `/config` with a source selector and source-specific removal while preserving existing source-less invocations as LeetCode operations.
- Create one APScheduler job per `(server_id, source)` and include the source in scheduled-delivery deduplication.
- Fetch scheduled daily data with the upstream `source` query parameter and render multi-problem responses with the existing overview UI.
- Migrate legacy `server_settings` schedules to `leetcode.com` after creating a database backup and validating the transactional copy.

## Capabilities

### New Capabilities

None. The change reuses the existing persistence, scheduling, command, API-client, and Discord UI owners.

### Modified Capabilities

- `database-layer`: Normalize guild settings and source-specific push settings, enforce supported sources and per-source uniqueness, and migrate legacy rows safely.
- `daily-schedule`: Manage and deliver one independent job per configured server/source pair.
- `slash-commands`: Configure, list, remove, and reset source-specific pushes through the existing `/config` command.
- `leetcode-client`: Fetch daily payloads by canonical daily source, including `sheep` and `0x3f`.

## Impact

- Affected code: `src/bot/utils/database.py`, `src/bot/cogs/slash_commands_cog.py`, `src/bot/cogs/interaction_handler_cog.py`, `src/bot/cogs/schedule_manager_cog.py`, `src/bot/api_client.py`, `src/bot/utils/ui_helpers.py`, and locale files.
- Affected schema assets: `data/init_db_schema.sql`, `data/cleanup_runtime_db.py`, and database schema tests.
- Affected documentation: OpenSpec capability specs and README server configuration examples.
- Compatibility: existing `/config channel:...`, `/config role:...`, `/config time:...`, and `/config timezone:...` invocations continue to target `leetcode.com`; every legacy schedule is migrated to that source.
- Data safety: the migration backs up the runtime database, copies and validates legacy schedules in one SQLite transaction, and removes the legacy table representation only after validation succeeds.
- Dependencies: no new runtime dependency or external service is introduced.

