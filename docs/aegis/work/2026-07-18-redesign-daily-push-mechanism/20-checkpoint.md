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
