# Redesign daily push mechanism - Checkpoint

- Task ID: 2026-07-18-redesign-daily-push-mechanism
- Current todo: Write and validate the approved OpenSpec design
- Active slice: Specification
- Blocked on: none
- Next step: Create proposal, design, and delta specs; validate and request written-spec review

## DriftCheckDraft

- Scope status: Specification remains within approved schema, config, scheduling, API, UI, tests, and docs scope
- Compatibility status: Source-less config targets leetcode.com and legacy rows migrate without data loss
- Retirement status: Legacy push columns have an approved backed-up transactional retirement path
- New risk signals:
- none
- Advisory decision: pause-for-user

## Checkpoint Update

- Current todo: Obtain user review of the written specification
- Active slice: Written specification review gate
- Completed todos:
- Explore current schema, scheduler, API, command, and test owners
- Confirm one push per source and independent per-push fields
- Approve normalized schema and explicit legacy migration
- Write and strictly validate OpenSpec proposal, design, and delta specs
- Evidence refs:
- openspec validate redesign-daily-push-mechanism --strict: valid
- aegis-workspace.py check --root .: passed
- Blocked on: User review of written specification
- Next step: After approval, use writing-plans to create the implementation plan

## DriftCheckDraft

- Scope status: Task 1 changed only canonical source identity and schema assets
- Compatibility status: Legacy cleanup conversion maps old schedules to leetcode.com
- Retirement status: No runtime legacy fallback added; runtime migration remains Task 2
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 2 runtime migration and normalized CRUD
- Active slice: Task 2 database migration and CRUD
- Completed todos:
- Task 1 canonical sources and normalized schema assets
- Evidence refs:
- tests/test_database_schema_assets.py: pass
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Write RED tests in tests/test_settings_database.py

## DriftCheckDraft

- Scope status: Task 2 stayed within SettingsDatabaseManager and focused database tests
- Compatibility status: Legacy rows preserve language and delivery fields as leetcode.com; source-less command compatibility remains for later task
- Retirement status: Legacy table is dropped only after backup and validation; combined CRUD removed from owner, callers pending
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 3 source-aware API and scheduled rendering
- Active slice: Task 3 daily API and rendering
- Completed todos:
- Task 1 canonical sources and schema assets
- Task 2 backed-up migration and normalized CRUD
- Evidence refs:
- settings/schema/path targeted pytest: pass
- targeted Ruff: pass
- Blocked on: none
- Next step: Write RED daily source request and multi-problem delivery tests

## DriftCheckDraft

- Scope status: Task 3 stayed within the API client, existing daily rendering owner, and focused tests
- Compatibility status: Manual domain calls remain unchanged; source requests use canonical source identity and source-scoped cache keys
- Retirement status: No alternate rendering protocol or API fallback was added
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 4 source-scoped scheduler jobs
- Active slice: Task 4 scheduler isolation
- Completed todos:
- Task 3 source-aware API access and scheduled single/multi-problem rendering
- Evidence refs:
- tests/test_daily_source_delivery.py and tests/test_daily_payload_reuse.py: pass
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Write RED scheduler tests for per-source job identity and isolation

## DriftCheckDraft

- Scope status: Task 4 stayed within scheduler ownership, the app reschedule adapter, and scheduler tests
- Compatibility status: Existing server-only reschedule calls rebuild all server pushes; callers may opt into targeted source rescheduling
- Retirement status: Server-only job IDs, combined settings reads, and hard-coded com delivery keys were removed
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 5 source-specific config command
- Active slice: Task 5 configuration and settings display
- Completed todos:
- Task 4 deterministic per-source jobs, targeted rescheduling, source-scoped delivery guards, and expected not-found handling
- Evidence refs:
- tests/test_schedule_manager_cog.py and tests/test_daily_source_delivery.py: pass
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Inspect config callback and write RED command tests for global language plus selected push

## DriftCheckDraft

- Scope status: Task 5 stayed within the config callback, existing settings embed owner, normalized CRUD example, and focused command tests
- Compatibility status: Source-less push fields target leetcode.com; language-only updates do not require or create a push
- Retirement status: All Python runtime and example calls to combined legacy settings CRUD are removed
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 6 confirmed source removal
- Active slice: Task 6 interaction routing and security checks
- Completed todos:
- Task 5 fixed source choices, source-specific create/update/removal request, global language, and multi-push settings display
- Evidence refs:
- tests/test_config_command.py, tests/test_settings_database.py, and tests/test_schedule_manager_cog.py: pass
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Write RED component tests for source removal and legacy reset preservation

## DriftCheckDraft

- Scope status: Task 6 stayed within interaction routing and its focused regression suite
- Compatibility status: Existing four-part reset IDs and whole-guild reset action remain unchanged
- Retirement status: Source removal has a distinct five-part route and cannot invoke whole-guild deletion
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Implement Task 7 localization and documentation
- Active slice: Task 7 locales, README, and strict spec validation
- Completed todos:
- Task 6 secure source removal confirmation with targeted deletion/rescheduling and legacy reset preservation
- Evidence refs:
- tests/test_interaction_handler.py and tests/test_config_command.py: pass
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Add locale parity and README assertions, then update all supported locales and configuration docs

## DriftCheckDraft

- Scope status: Task 7 changed only supported locale resources, README usage/migration documentation, and focused documentation tests
- Compatibility status: Existing reset and configuration keys remain; new source-specific keys are present in all three locales
- Retirement status: README documents backed-up one-way migration to leetcode.com rather than runtime fallback behavior
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Run Task 8 full regression and retirement verification
- Active slice: Task 8 completion evidence
- Completed todos:
- Task 7 locale parity, README multi-source workflow, and migration documentation
- Evidence refs:
- tests/test_source_layout_phase56.py, tests/test_config_command.py, and tests/test_interaction_handler.py: pass
- openspec validate redesign-daily-push-mechanism --strict: valid
- targeted Ruff check and format: pass
- Blocked on: none
- Next step: Load verification-before-completion instructions and run every final verification command
