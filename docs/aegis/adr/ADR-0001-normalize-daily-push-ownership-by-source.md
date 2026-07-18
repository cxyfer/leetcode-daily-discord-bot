# ADR-0001 - Normalize daily push ownership by source

Status: `recorded-from-work`
Date: `2026-07-18`

## Source Evidence

- Implemented and verified work in docs/aegis/work/2026-07-18-redesign-daily-push-mechanism plus commits c7a61c3 through 2b8165e.
## Context

The former server_settings row owned guild language and one delivery schedule, preventing independent leetcode.com, sheep, and 0x3f pushes. The redesign requires at most one push per supported source with independent delivery fields and shared guild language.

## Decision

Keep guild language in server_settings and make daily_push_settings the sole delivery owner, keyed by (server_id, source) with a fixed three-source constraint. Migrate each legacy schedule transactionally to leetcode.com after creating a timestamped SQLite backup, then remove legacy delivery columns and fallback access.

## Alternatives Considered

- Keep one combined server_settings row and add three sets of source-specific columns; rejected because it multiplies nullable columns and couples guild and delivery ownership.
- Store arbitrary push rows without a fixed source constraint; rejected because the product limit is exactly one push for each of three supported sources and database enforcement prevents drift.
## Consequences

- Each server can configure up to three independently scheduled pushes while language remains shared.
- Scheduler job identity, delivery deduplication, configuration, and API requests must carry canonical source identity end to end.
- Legacy migration is one-way in the runtime database; rollback uses the retained pre-migration backup.
## Compatibility Boundary

Source-less /config delivery edits continue to target leetcode.com, existing manual domain-based /daily calls remain unchanged, and legacy reset IDs remain accepted.

## Retirement Impact

Retire delivery columns from server_settings, combined settings CRUD, server-only scheduler job IDs, hard-coded com delivery keys, and all runtime fallback reads after validated migration.

## Baseline Sync

- Needed: needed
- Target: openspec/changes/redesign-daily-push-mechanism/design.md, data/init_db_schema.sql, and README.md
- Action: cite unchanged
- Reason: The approved OpenSpec design, normalized schema assets, and operator documentation were updated in the same change and already state the implemented owner, contract, compatibility, and retirement boundaries.

## Evidence References

- openspec/changes/redesign-daily-push-mechanism/design.md
- tests/test_settings_database.py
- tests/test_schedule_manager_cog.py
- tests/test_config_command.py
## Boundary

This ADR is an advisory Aegis Method Pack record. It does not grant completion authority or replace project-authoritative architecture sources.
