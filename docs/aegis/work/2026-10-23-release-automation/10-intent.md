# Release automation intent

Apply the reviewed oj-api-rs #45 release process to this bot, adapting Python/uv metadata and offline startup validation. Authority is the user request and the scoped implementation plan; source commit `1be7e2d` is immutable review evidence.

The existing `ghcr.yml` remains the single publisher. Release helpers do not own application runtime or persistent data. Preserve exact image names and historical notes; only the newest stable release may update `latest`. No version bump, tag, merge, production publication or source-repository change is included.

Before edits, `ci/release-automation` was clean at `3928aee3`, tracking `origin/main` with no divergence or Git operation; the main checkout remained on `main`. Base runtime tests passed 204 cases. The task worktree was required by user Git rules and was verified ignored.

Read baseline: README, Dockerfile, requirements, current CI/GHCR workflows, pyproject/uv identity, bootstrap, app/database initialization and source PR documents. Baseline authority and architecture ownership are aligned; no missing reference blocks execution. TDD is off with post-change behavioral regression tests. Architecture review applies to publication permissions, queueing and preservation of release notes.

Success requires focused/full tests, pinned lint, independent review, a pushed branch and unmerged PR, plus actual hosted image build and offline smoke evidence. Formal tag-triggered writes remain outside verification.

## BaselineUsageDraft

- Required baseline refs:
- docs/aegis/plans/2026-10-23-release-automation.md
- .github/workflows/ghcr.yml
- pyproject.toml
- uv.lock
- Delivered context refs:
- none
- Acknowledged before plan:
- README.md
- Dockerfile
- src/bot/app.py
- Cited in plan:
- oj-api-rs:1be7e2dc
- Missing refs:
- none
- Advisory decision: continue
