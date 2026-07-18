# Redesign daily push mechanism - Reflection

## Outcome

- Normalized guild language and source-specific delivery ownership are implemented for `leetcode.com`, `sheep`, and `0x3f`.
- Legacy schedules migrate transactionally to `leetcode.com` after a timestamped backup and no normal runtime fallback remains.
- Scheduler, configuration, removal confirmation, rendering, localization, and documentation carry canonical source identity end to end.

## Architecture Review

- Ownership integrity: `server_settings` owns guild language, `daily_push_settings` owns delivery, and `daily_sources.py` owns source identity.
- Module boundaries: database, scheduler, API, commands, interactions, and UI remain in their existing owners; the app helper is wiring only.
- Contract changes: normalized schema, source-aware API, job IDs, `/config`, compatibility, and migration behavior are documented in OpenSpec, README, and ADR-0001.
- Cascade proliferation: source identity is passed through the expected call chain without a second scheduler, command, or rendering protocol.
- Dependency direction: cogs depend on stable utility contracts; persistence does not depend on command or scheduler layers.
- Retirement completeness: combined CRUD, legacy delivery columns in the live table, server-only job IDs, and hard-coded `com` delivery guards are removed; legacy column reads exist only in the one-way migration owner.
- Entropy flow: normalized ownership and a single source validator replace combined state and scattered literals; no fallback or dual-write path was added.

## Complexity Closure

- Budget status: exceeded-and-governed.
- Governed now: large files received only behavior within their existing owner; overview rendering and confirmation patterns were reused; focused tests were split into new files.
- Deferred follow-up: `src/bot/utils/ui_helpers.py` is 1225 lines and should eventually be split by UI domain; `slash_commands_cog.py` is 776 lines and should be monitored before adding another major command workflow.
- Completion impact: complete for the approved redesign; complexity follow-up is non-blocking.

## Risk And Unknowns

- Automated tests mock Discord and the upstream API; no live guild delivery or production database migration was executed in this workspace.
- Rollback depends on retaining the generated `.pre-push-redesign.bak` file and operator action; the normal runtime intentionally never reads it.
- A real upstream source can legitimately have no daily payload; scheduler behavior is an expected no-delivery rather than a failure.

## Deeper Cause

The former schema made a guild row own both global language and one schedule. The redesign fixes that ownership mismatch rather than adding three nullable schedule slots or runtime compatibility fallbacks.

Method Pack output does not grant completion authority.
