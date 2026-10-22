# Port the reviewed release workflow

## Goal and authority

Apply the user-requested oj-api-rs #45 release process to this bot after reviewing it. The mistaken bot PR #46 is closed and was never merged. Reference: oj-api-rs head `1be7e2d`, merged as `577d6a47`; its 18 tests and independent workflow review found no blocking issues.

## Architecture and baseline

Keep `.github/workflows/ghcr.yml` as the only versioned-image publisher. Port its standard-library notes helper, tests, English template and operator guide. Adapt version identity from Cargo to `[project]` in `pyproject.toml` and the root package in `uv.lock`. Python `2.2.0rc1` corresponds to tag `v2.2.0-rc.1`.

The bot base is `origin/main` at `3928aee3`; `main` is the default branch and existing CI validates PRs targeting it. The worktree is `.worktrees/release-automation`, branch `ci/release-automation`. Existing application tests: 204 passed. Read baselines: current workflow, Dockerfile, requirements, manifests, launcher, bootstrap, database initialization and README. No project release-governance document existed before this task.

## Compatibility and minimum change

The current tag workflow always moves `latest` and cannot create notes, so documentation alone cannot deliver the requested behavior. Limit code changes to one release helper and its tests, plus the existing workflow. Preserve image names, existing runtime, databases, secrets, historical changelog and current CI branch filters. Do not bump a version, create a release tag, publish a production image/release, merge the new PR, or change either existing feature PR.

Stable and RC tags publish their exact image before creating a draft. Only the newest stable tag updates `latest`. Reruns preserve existing draft/published notes and publication status. PR/manual validation builds publish nothing. Smoke tests use a disposable container with networking disabled and no credentials; execute the real launcher and verify fresh SQLite initialization and packaged imports. There are no dev/nightly image channels to port in this repository.

TDD Route: mode off; decision skipped; no strict authority. Add meaningful post-change behavioral tests for Python manifest/lock matching, RC normalization and existing release behavior. Architecture review is required for workflow permissions and release ordering. The existing publisher remains canonical; no second publisher or compatibility fallback is introduced.

## Tasks and verification

1. Port the release helper/template and tests; adapt metadata identity and test fixtures for Python and uv. Run `python3 -S scripts/test_release_notes.py -v`, including malformed/mismatched metadata and normalized RC versions.
2. Adapt the existing GHCR workflow with validation-only PR/manual runs, serialized releases, exact/stable tags, image build, offline smoke test, optional validation artifact, and draft creation after image publication. Check YAML, actionlint/ShellCheck, and current GitHub schema for `concurrency.queue: max`.
3. Document Python version preparation, tag/image mapping, manual retries, English draft editing/publication and preserved reruns in `RELEASING.md`; link it from README without changing historical notes.
4. Run pinned Ruff, full bot tests, helper tests, diff checks and an independent review. Commit using repository gitmoji style, push the task branch, open a PR against `main`, and observe hosted CI and the image build/smoke test.

## Risks and completion boundary

Local Docker is unavailable; hosted PR image validation is required before declaring the image verified. Actual tag-triggered GHCR writes and GitHub draft creation remain unexecuted unless a specific release is authorized. Keep that limitation explicit. No review finding justifies editing the source oj-api-rs repository. Execute inline with independent final review; no user confirmation is needed within this authorized scope.
