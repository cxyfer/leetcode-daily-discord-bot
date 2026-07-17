# Implement /daily_extra command - Checkpoint

- Task ID: 2026-07-16-implement-daily-extra-command
- Current todo: Task 1: source-only API method and target-aware daily payload
- Active slice: API/payload tests and implementation
- Blocked on: none
- Next step: Run focused clean baseline tests, then write Task 1 RED tests

## Checkpoint Update

- Current todo: Task 2 overview button safety and footer support
- Active slice: Task 2
- Completed todos:
- Task 1 API source method and target-aware daily payload implemented
- Evidence refs:
- Task 1 focused regression: 29 passed
- Blocked on: none
- Next step: Add failing overview tests, then implement all-or-nothing button validation

## Checkpoint Update

- Current todo: Task 3 slash command and localization
- Active slice: Task 3
- Completed todos:
- Task 2 all-or-nothing overview buttons and footer override implemented
- Evidence refs:
- Task 2 focused regression: 40 passed
- Blocked on: none
- Next step: Add command acceptance tests, then implement /daily_extra and locale keys

## Checkpoint Update

- Current todo: Task 4 privacy characterization, docs, and completion verification
- Active slice: Task 4
- Completed todos:
- Task 3 manual /daily_extra command and three-locale strings implemented
- Evidence refs:
- Task 3 tests: 31 passed; focused Ruff passed
- Blocked on: none
- Next step: Lock private independent detail clicks, update README, then run full verification

## DriftCheckDraft

- Scope status: manual daily_extra only; no scheduler DB config or new interaction route
- Compatibility status: existing daily daily_cn schedule and v0.4 compatibility focused regressions pass
- Retirement status: no owner or path retired; unified problem view route reused
- New risk signals:
- three pre-existing path assertions fail because worktree runtime assets are symlinked to main checkout
- Advisory decision: continue

## Checkpoint Update

- Current todo: No implementation work remains; preserve worktree for user handoff
- Active slice: Closeout
- Completed todos:
- Tasks 1-4 and all approved implementation scope completed
- Evidence refs:
- 86 focused tests pass; Ruff and OpenSpec pass; full suite 229 pass with 3 worktree symlink baseline failures
- Blocked on: none
- Next step: User may request commit or PR after reviewing the documented baseline-only test failures
