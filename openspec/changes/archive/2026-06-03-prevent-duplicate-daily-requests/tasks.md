## 1. Scheduler overlap control

- [x] 1.1 Update scheduled daily job defaults to prevent overlapping instances and coalesce missed runs.
- [x] 1.2 Add tests or assertions covering `coalesce=True`, `max_instances=1`, and existing misfire grace behavior.

## 2. Daily payload reuse

- [x] 2.1 Add a small in-memory daily payload cache keyed by domain and resolved date.
- [x] 2.2 Add in-flight payload coalescing so concurrent identical daily payload requests share the same work.
- [x] 2.3 Refactor current and date-specific daily rendering paths to use the shared payload helper while still building localized embeds per request.
- [x] 2.4 Add async tests proving concurrent identical payload requests do not duplicate daily/history API fetches.

## 3. Scheduled delivery duplicate guard

- [x] 3.1 Add an in-memory scheduled delivery guard keyed by server id, channel id, domain, and daily date.
- [x] 3.2 Ensure duplicate scheduled delivery attempts are skipped with a log message while the original delivery is in progress.
- [x] 3.3 Ensure delivery guard keys are cleaned up after success, failure, processing skip, or rate-limit skip.
- [x] 3.4 Add tests covering duplicate scheduled delivery skip and cleanup after exceptions.

## 4. Manual daily behavior preservation

- [x] 4.1 Verify manual `/daily` and `/daily_cn` still return a response for each valid interaction.
- [x] 4.2 Verify date-specific `/daily date:YYYY-MM-DD` still works and uses the shared payload path where applicable.
- [x] 4.3 Verify public and ephemeral response behavior remains unchanged.

## 5. Validation

- [x] 5.1 Run the focused test suite for daily commands, scheduler behavior, and shared UI helpers.
- [x] 5.2 Run `uv run --extra dev pytest` for the full test suite.
- [x] 5.3 Run `uv run ruff check .` to confirm lint quality.
