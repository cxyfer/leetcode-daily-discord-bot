# Port reviewed release automation - Checkpoint

- Task ID: 2026-10-23-release-automation
- Current todo: Define first execution slice.
- Active slice: initial
- Blocked on: none
- Next step: Read baseline refs and start the next safe slice.

## Checkpoint Update

- Current todo: Create PR and observe hosted image validation
- Active slice: hosted-verification
- Completed todos:
- Closed mistaken PR 46 without merging
- Reviewed source and ported release behavior with Python/uv metadata
- 20 helper tests, 204 runtime tests, pinned Ruff and independent review pass
- Evidence refs:
- none
- Blocked on: none
- Next step: Commit, push and open PR against main

## DriftCheckDraft

- Scope status: Matches approved release-tooling scope
- Compatibility status: Runtime and exact image names preserved; latest restricted to stable
- Retirement status: Existing workflow replaced in place; no competing publisher retained
- New risk signals:
- none
- Advisory decision: continue

## Checkpoint Update

- Current todo: Commit and create PR after automatic approval service is repaired
- Active slice: approval-blocked
- Completed todos:
- Closed mistaken PR 46 without merging; branch retained
- Reviewed source release flow and implemented bot adaptation
- 20 helper tests, 204 runtime tests, pinned Ruff, actionlint and independent review pass
- Evidence refs:
- none
- Blocked on: Automatic approval review failed: configured gpt-6-luna returned 404; git commit was not executed
- Next step: Resolve approval service error, then commit, push, open PR and observe hosted build

## Checkpoint Update

- Current todo: Observe hosted image validation for PR 47
- Active slice: hosted-verification
- Completed todos:
- Automatic approval retry succeeded without changing the configured gpt-6-luna reviewer
- Committed 2302cbc and pushed ci/release-automation
- Opened PR 47 against main; hosted Ruff, pytest and release-helper tests pass
- Evidence refs:
- none
- Blocked on: none
- Next step: Record actual Docker build/smoke result and update PR validation

## Checkpoint Update

- Current todo: Finalize verification record and retain open PR 47
- Active slice: closeout
- Completed todos:
- Hosted runtime CI passes at 2302cbc
- Hosted image build, offline launcher/SQLite smoke and image export pass in run 39851777266
- Automatic approval recovered with gpt-6-luna configuration unchanged
- Evidence refs:
- GitHub Actions 39851777181 and 39851777266
- Blocked on: none
- Next step: Commit this evidence-only update, verify final-head checks and remove the clean temporary worktree
