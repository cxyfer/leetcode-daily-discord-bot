## 1. Canonical Sources And Schema

- [x] 1.1 Add one canonical daily-source constants/validation owner.
- [x] 1.2 Normalize runtime init SQL into guild settings and source-specific push settings.
- [x] 1.3 Update cleanup/rebuild handling for both legacy and normalized inputs.
- [x] 1.4 Add schema asset and constraint coverage.

## 2. Database Migration And CRUD

- [x] 2.1 Add backed-up transactional legacy migration with row identity/count validation.
- [x] 2.2 Add normalized guild-language and daily-push CRUD methods.
- [x] 2.3 Remove internal reliance on combined legacy settings CRUD.
- [x] 2.4 Add migration, rollback, idempotency, constraint, and CRUD tests.

## 3. Daily API And Rendering

- [x] 3.1 Add canonical `source` daily API requests without breaking domain calls.
- [x] 3.2 Scope daily payload reuse by canonical source/domain identity.
- [x] 3.3 Render multi-problem scheduled payloads with existing overview helpers.
- [x] 3.4 Preserve single-problem, locale, role mention, and 202/404 behavior.

## 4. Scheduler

- [x] 4.1 Create deterministic jobs per `(server_id, source)`.
- [x] 4.2 Add targeted source reschedule/removal and whole-server reschedule.
- [x] 4.3 Include source in delivery deduplication and logs.
- [x] 4.4 Add startup, isolation, error, retry, and deduplication tests.

## 5. Configuration And Confirmations

- [x] 5.1 Extend `/config` with fixed source choices and source-specific removal.
- [x] 5.2 Preserve source-less LeetCode edits and global language updates.
- [x] 5.3 Display guild language plus all independent push settings.
- [x] 5.4 Add secure source-removal confirmation while preserving reset.
- [x] 5.5 Add command and interaction regression tests, including custom-ID limits.

## 6. Localization And Documentation

- [x] 6.1 Add equivalent user-facing keys to all supported locales.
- [x] 6.2 Update README configuration examples and migration behavior.
- [x] 6.3 Validate locale parity and strict OpenSpec consistency.

## 7. Verification And Retirement

- [x] 7.1 Run targeted schema, migration, API, rendering, scheduler, command, and interaction tests.
- [x] 7.2 Run the full test suite and Ruff checks.
- [x] 7.3 Verify no runtime reads or writes legacy push columns or server-only job IDs.
- [x] 7.4 Complete architecture, complexity, migration-safety, and evidence review.
