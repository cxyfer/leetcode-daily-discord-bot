# Release automation evidence

- Source: reviewed oj-api-rs #45 at `1be7e2d` (merged as `577d6a47`); 18 helper tests pass. Independent workflow review found no actionable issue.
- Bot: `python3 -S scripts/test_release_notes.py -q`: 20 passed, including Python RC identity and mismatched/missing/duplicate lock packages.
- Runtime: isolated locked test environment ran the full existing suite: 204 passed. Runtime source files are unchanged.
- Ruff 0.14.10 (the lockfile version): check passes; all 46 Python files already formatted.
- actionlint 1.7.12 and ShellCheck 0.11.0 pass with one narrow exception for the supported `concurrency.queue: max` schema field. Current official GitHub docs explicitly document it with `cancel-in-progress: false`.
- Workflow bootstrap assertions pass against an isolated archive, initializing fresh SQLite, loading packaged locales and importing command modules without a token. Local Docker is unavailable, so this does not yet prove a container build.
- Live read-only generation for `v2.1.0` selects `v2.0.2...v2.1.0`, includes PRs and direct commits, and creates only a local editable file.
- Diff validation passes with `core.whitespace=cr-at-eol` because the existing README uses CRLF. Aegis structural validation passes.
- Independent review of the port found no actionable issue. Hosted PR checks are the remaining completion check.

Actual version tags, production image pushes, GitHub draft creation and publication have not been executed. Existing release notes have not been modified. The mistaken bot PR #46 is closed and unmerged; branch deletion was rejected by automatic approval review and the branch is retained.

Commit attempt was not executed: automatic approval review returned HTTP 404 for configured gpt-6-luna. No push or PR creation was attempted after that failure. Hosted image verification is blocked until the approval service is repaired.

Approval retry recovered: commit `2302cbc` and the branch push succeeded. Reviewer configuration still selects `gpt-6-luna`; no model override was changed. PR #47 targets `main`. Hosted CI run `39851777181` passes at that commit, and prepare/helper checks in run `39851777266` pass. The image job is still running.

Hosted image verification completed successfully at `2302cbc`: run `39851777266`, job `120079644397`, built the real Docker image, executed the offline launcher/import/locale/SQLite assertions and exported/uploaded the image. Artifact `12456769633` (`leetcode-daily-discord-bot-validation-image`, 67,563,258 bytes) is retained for three days. Release publication jobs were correctly skipped for the PR. Runtime CI run `39851777181` also passed. No review threads are outstanding. Actual versioned publication remains outside verification.
