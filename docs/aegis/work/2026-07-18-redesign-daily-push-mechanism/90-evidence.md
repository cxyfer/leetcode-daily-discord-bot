# Redesign daily push mechanism - Evidence

No evidence has been recorded yet.

## EvidenceBundleDraft

- Artifact key: openspec-strict-validation
- Type: command
- Source: openspec validate redesign-daily-push-mechanism --strict
- Summary: OpenSpec change is valid
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: aegis-workspace-check
- Type: command
- Source: aegis-workspace.py check --root .
- Summary: Aegis workspace structure is valid
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: task1-schema-assets-green
- Type: command
- Source: uv run pytest tests/test_database_schema_assets.py; ruff targeted checks
- Summary: Normalized schema, constraints, and legacy cleanup conversion tests pass; targeted lint and format pass
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: task2-database-green
- Type: command
- Source: uv run pytest tests/test_settings_database.py tests/test_database_schema_assets.py tests/test_bootstrap_and_paths.py; targeted Ruff
- Summary: Runtime backup/migration/rollback/idempotency and normalized settings CRUD tests pass; targeted lint and format pass
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: task3-daily-source-delivery-green
- Type: command
- Source: uv run pytest tests/test_daily_source_delivery.py tests/test_daily_payload_reuse.py; targeted Ruff
- Summary: Source API params, domain compatibility, cache isolation, single/multi-problem rendering, role mention, and source-not-found propagation pass
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: task4-source-scoped-scheduler-green
- Type: command
- Source: uv run pytest tests/test_schedule_manager_cog.py tests/test_daily_source_delivery.py; targeted Ruff
- Summary: Startup jobs, job identity, targeted and whole-server rescheduling, source-scoped deduplication, retry, not-found skip, and source forwarding pass
- Verifier: Codex

## EvidenceBundleDraft

- Artifact key: task5-source-config-green
- Type: command
- Source: uv run pytest tests/test_config_command.py tests/test_settings_database.py tests/test_schedule_manager_cog.py; targeted Ruff
- Summary: Fixed source choices, LeetCode default updates, three-source creation, partial updates, global language, removal confirmation IDs, and multi-push display pass
- Verifier: Codex
