# Redesign Daily Push Mechanism Implementation Plan

## Goal

Implement the approved `redesign-daily-push-mechanism` OpenSpec change so each Discord server can configure one independent scheduled push for each of `leetcode.com`, `sheep`, and `0x3f`, while preserving guild language and every legacy LeetCode push through a backed-up transactional migration.

## Architecture

Normalize persistence into guild-wide `server_settings` and source-specific `daily_push_settings`. Route canonical daily-source values through a small shared constants owner. Keep `/config` as the public configuration owner, APScheduler as the job owner, `OjApiClient` as the upstream contract owner, and existing `ui_helpers` functions as the rendering owner. Retire legacy schedule columns after a validated migration; do not add fallback reads or dual writes.

## Tech Stack

Python 3.10+, SQLite, discord.py application commands and components, APScheduler `AsyncIOScheduler`, pytest/pytest-asyncio, Ruff, OpenSpec.

## Baseline / Authority Refs

- `openspec/changes/redesign-daily-push-mechanism/proposal.md`
- `openspec/changes/redesign-daily-push-mechanism/design.md`
- `openspec/changes/redesign-daily-push-mechanism/specs/database-layer/spec.md`
- `openspec/changes/redesign-daily-push-mechanism/specs/daily-schedule/spec.md`
- `openspec/changes/redesign-daily-push-mechanism/specs/slash-commands/spec.md`
- `openspec/changes/redesign-daily-push-mechanism/specs/leetcode-client/spec.md`
- Current capability baselines under `openspec/specs/`

## Compatibility Boundary

- Existing `/config` push updates without `source` continue to target `leetcode.com`.
- Existing guild language is preserved and remains shared by all pushes.
- Every legacy schedule becomes exactly one `leetcode.com` push.
- Existing manual `/daily` and `/daily_cn` domain calls remain unchanged.
- Existing LeetCode single-problem scheduled output remains unchanged.
- No runtime fallback reads or writes legacy push columns after migration.

## Verification

```bash
uv run pytest tests/test_settings_database.py tests/test_database_schema_assets.py
uv run pytest tests/test_daily_source_delivery.py tests/test_daily_payload_reuse.py
uv run pytest tests/test_schedule_manager_cog.py
uv run pytest tests/test_config_command.py tests/test_interaction_handler.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
openspec validate redesign-daily-push-mechanism --strict
python3 /home/usaya/.codex/aegis/scripts/aegis-workspace.py check --root .
```

Expected final result: all commands exit `0`; pytest reports no failures; OpenSpec reports the change valid; the Aegis workspace check passes.

## Plan Basis

- Requirement status: approved by the user after written-spec review.
- Facts: current persistence and scheduler identities are server-only; upstream daily data accepts canonical `source` and may contain multiple problems.
- Assumptions: the bot remains a single-process runtime with MemoryJobStore; no distributed delivery guarantee is required.
- Unknowns to resolve through RED tests: exact legacy backup filename assertions and Discord command callback invocation mechanics.

## Change Necessity

- User-visible need: independently configure and deliver three daily sources.
- No-change option: impossible because the current primary key and scheduler job ID permit only one push per server.
- Minimum change boundary: persistence/schema assets, `/config`, reset/removal interactions, scheduler, API source query, scheduled rendering, locales, tests, and README.
- Decision: `code-change`.

## Existence Check

- Proposed surface: `src/bot/utils/daily_sources.py`.
- Reuse candidates: `ui_constants.py`, `config.py`, or duplicate literals.
- Why insufficient: source identity is a domain contract shared by persistence, API, scheduler, commands, and UI rather than UI-only or process configuration.
- Creation proof: a single constants/validation owner prevents five modules from drifting on canonical values and default mapping.
- Retirement impact: no old owner exists; scattered source literals introduced during the change are forbidden.
- Decision: `add-with-proof`.

## Architecture Integrity Lens

- Invariant: at most one push per `(server_id, supported_source)` and at most three per server.
- Canonical owners: `server_settings` for language; `daily_push_settings` for delivery; `daily_sources.py` for source identity.
- Responsibility overlap: none after legacy push columns are retired.
- Higher-level simplification: scheduler and `/config` consume the same push record shape returned by the database.
- Retirement: legacy table representation is dropped only after backup and migration validation.
- Verdict: normalized owner split is coherent; proceed.

## Plan-Time Complexity Check

- `src/bot/utils/ui_helpers.py`: 1,145 lines, strong pressure. Modify only existing daily/settings helpers; do not add configuration orchestration.
- `src/bot/cogs/slash_commands_cog.py`: 694 lines, moderate pressure. Keep public callback wiring in place but extract small private parsing/rendering helpers within the class or a focused helper module only if the touched block exceeds roughly 80 cohesive lines.
- `src/bot/utils/database.py`: 402 lines, acceptable. Keep migration and settings CRUD together because they share the SQLite contract.
- `src/bot/cogs/schedule_manager_cog.py`: 241 lines, acceptable and correct owner for job identity/lifecycle.
- Recommendation: add `daily_sources.py`; edit other owners in place; create focused test files instead of growing unrelated large suites.

## Execution Readiness View

- Intent Lock: three supported pushes, one per source, independent delivery fields, shared language.
- Scope Fence: no manual `/daily_extra`, arbitrary sources, distributed idempotency, or upstream calendar duplication.
- Baseline Lock: approved OpenSpec change at commit `eda46ec`.
- Owner constraints: no dual persistence owners; no caller-side legacy fallback.
- Compatibility: source-less `/config` means LeetCode; manual domain calls remain.
- Retirement: backup, copy, validate, drop legacy representation in one transaction.
- Task batches: constants/schema; DB migration/CRUD; API/rendering; scheduler; commands/interactions; locales/docs/spec checklist; full verification.
- Test obligations: RED before each behavior slice, targeted GREEN, then full suite and lint.
- Drift rule: return to design if a fourth source, duplicate same-source push, persistent history, or new public command becomes necessary.
- Completion evidence: fresh command output for all verification commands.

## Task 1: Establish Canonical Source Identity And Normalized Schema Assets

**Files:**

- Create `src/bot/utils/daily_sources.py`
- Modify `data/init_db_schema.sql`
- Modify `data/cleanup_runtime_db.py`
- Modify `tests/test_database_schema_assets.py`

**Why:** The database must enforce the supported-source set and per-source uniqueness before higher layers can depend on it.

**Impact / Compatibility:** New databases use normalized tables. The cleanup utility must preserve both normalized databases and legacy schedules as `leetcode.com`.

**Verification:** `uv run pytest tests/test_database_schema_assets.py`

- [x] Write failing schema tests asserting `daily_push_settings`, composite primary key, source `CHECK`, foreign key cascade, updated target tables, normalized cleanup copies, and legacy cleanup conversion.
- [x] Run the verification command and confirm failures reference missing `daily_push_settings`/legacy conversion.
- [x] Add `DEFAULT_DAILY_PUSH_SOURCE = "leetcode.com"`, immutable supported-source values, choice labels, and a validation helper; update init SQL and cleanup rebuild logic to use the approved schema and legacy conversion.
- [x] Re-run the verification command and confirm all schema asset tests pass.
- [x] Commit with `🧪 test(db): define normalized push schema assets` or the closest repository-history style.

## Task 2: Implement Backed-Up Transactional Migration And Settings CRUD

**Files:**

- Modify `src/bot/utils/database.py`
- Create `tests/test_settings_database.py`
- Modify `tests/test_bootstrap_and_paths.py` only if path-safe backup behavior needs coverage there

**Why:** Runtime startup must safely migrate real legacy data and expose source-specific CRUD as the sole settings contract.

**Impact / Compatibility:** Replace the old combined getters/setters with guild and push operations while retaining `get_server_settings(server_id)` as the locale-compatible guild lookup. Existing callers migrate in later tasks within the same branch.

**Target API:**

```python
get_server_settings(server_id) -> dict | None
set_server_language(server_id, language) -> bool
get_daily_push(server_id, source) -> dict | None
get_daily_pushes(server_id) -> list[dict]
get_all_daily_pushes() -> list[dict]
set_daily_push(server_id, source, channel_id, role_id=None,
               post_time="00:00", timezone="UTC") -> bool
delete_daily_push(server_id, source) -> bool
delete_server_settings(server_id) -> bool
```

`get_all_daily_pushes()` returns push fields plus joined `language`.

**Verification:** `uv run pytest tests/test_settings_database.py tests/test_database_schema_assets.py tests/test_bootstrap_and_paths.py`

- [ ] Write failing tests for new-schema CRUD isolation, default language creation, unsupported source rejection, cascade reset, legacy backup creation, exact legacy-to-LeetCode copy, idempotent restart, and transaction rollback under injected validation failure.
- [ ] Run the verification command and confirm failures arise from missing migration/CRUD behavior.
- [ ] Centralize settings connections with `PRAGMA foreign_keys = ON`; implement schema detection, SQLite backup, transactional table rebuild and validation, and the target CRUD API using parameterized queries.
- [ ] Re-run the verification command and confirm migration and CRUD tests pass without changing LLM cache behavior.
- [ ] Commit with `✨ feat(db): normalize daily push settings`.

## Task 3: Add Source-Aware Daily API Access And Scheduled Rendering

**Files:**

- Modify `src/bot/api_client.py`
- Modify `src/bot/utils/ui_helpers.py`
- Modify `tests/test_daily_payload_reuse.py`
- Create `tests/test_daily_source_delivery.py`

**Why:** Sheep and 0x3f must be requested with `source`, preserve multiple ordered problems, and render through existing overview controls.

**Impact / Compatibility:** Existing `get_daily(domain, date)` and manual domain helpers stay valid. New source calls must not send `domain`. Payload cache keys must distinguish canonical source from domain aliases.

**Target API:**

```python
async def get_daily(
    self,
    domain: str = "com",
    date: str | None = None,
    *,
    source: str | None = None,
) -> dict | None:
    ...

async def send_daily_challenge(
    *,
    bot,
    interaction=None,
    channel_id=None,
    role_id=None,
    guild_locale=None,
    daily_source="leetcode.com",
):
    ...
```

**Verification:** `uv run pytest tests/test_daily_source_delivery.py tests/test_daily_payload_reuse.py`

- [ ] Write failing tests proving `source=sheep|0x3f` request params, domain compatibility, envelope preservation, cache-key isolation, single-problem existing rendering, multi-problem overview/view reuse, role mention, and distinguishable 404 handling.
- [ ] Run the verification command and confirm the new source/rendering tests fail for the expected missing arguments and single-problem assumption.
- [ ] Extend `OjApiClient.get_daily()` and the existing daily payload/send helpers; reuse `create_problems_overview_embed()` and `create_problems_overview_view()` without adding new UI protocols.
- [ ] Re-run the verification command and confirm both new and existing daily payload tests pass.
- [ ] Commit with `✨ feat(daily): support source-aware push rendering`.

## Task 4: Make Scheduler Jobs Independent By Server And Source

**Files:**

- Modify `src/bot/cogs/schedule_manager_cog.py`
- Modify `src/bot/app.py`
- Modify `tests/test_schedule_manager_cog.py`

**Why:** Persistence can own three rows only if job identity, rescheduling, delivery guards, logs, and failures are source-scoped.

**Impact / Compatibility:** The app-level reschedule helper accepts an optional source. Omitting source reschedules all pushes for the server, preserving reset behavior; source-specific configuration passes the selected source.

**Target signatures:**

```python
async def reschedule_daily_challenge(server_id: int | None = None,
                                     source: str | None = None): ...
async def send_daily_challenge_job(server_id: int, source: str,
                                   channel_id: int, role_id: int | None,
                                   timezone_str: str): ...
```

Job IDs use a deterministic helper such as `daily_challenge:{server_id}:{source}`. Delivery keys are `(server_id, channel_id, source, date)`.

**Verification:** `uv run pytest tests/test_schedule_manager_cog.py tests/test_daily_source_delivery.py`

- [ ] Extend failing scheduler tests for three startup jobs, deterministic IDs, targeted reschedule/removal, peer-source survival after invalid config, source-scoped deduplication, 404 skip, and source forwarding.
- [ ] Run the verification command and confirm failures show server-only job identity and hard-coded `com` delivery.
- [ ] Refactor job creation/rescheduling around daily push records, pass canonical source through delivery, and treat upstream not-found as expected no-delivery while preserving 202 retry and rate-limit handling.
- [ ] Re-run the verification command and confirm all scheduler tests pass.
- [ ] Commit with `✨ feat(schedule): isolate jobs by daily source`.

## Task 5: Redesign `/config` Around Global Language And Selected Push

**Files:**

- Modify `src/bot/cogs/slash_commands_cog.py`
- Modify `src/bot/utils/ui_helpers.py`
- Create `tests/test_config_command.py`

**Why:** Administrators need one backward-compatible command to list, create, partially update, and request removal of independent source pushes.

**Impact / Compatibility:** No-source push edits map to `leetcode.com`. Language-only updates need no channel. New pushes require channel. `remove` requires explicit source. Existing permission, time, timezone, and role validation remains.

**Command additions:**

```python
source: str | None = None
remove: bool = False
```

Use fixed `app_commands.Choice` values from the canonical source owner. Keep `reset` whole-guild. Settings display passes one language value and ordered push records to a revised settings embed helper.

**Verification:** `uv run pytest tests/test_config_command.py`

- [ ] Write failing callback/helper tests for list, legacy default source, each source create, partial update, language-only update, first-source channel requirement, role conflict, remove-without-source rejection, remove/reset conflict, and custom-ID length.
- [ ] Run the verification command and confirm failures reflect the old combined row model.
- [ ] Refactor `/config` input classification, persistence calls, source-specific reschedule calls, and settings rendering while keeping changes out of unrelated slash commands.
- [ ] Re-run the verification command and confirm all command tests pass.
- [ ] Commit with `✨ feat(config): manage source-specific pushes`.

## Task 6: Add Confirmed Source Removal And Preserve Whole-Guild Reset

**Files:**

- Modify `src/bot/cogs/interaction_handler_cog.py`
- Modify `tests/test_interaction_handler.py`

**Why:** Destructive source removal needs the same requester, permission, guild, and expiry protections as reset without weakening reset semantics.

**Impact / Compatibility:** Existing `config_reset_{confirm|cancel}|guild|user|expiry` IDs remain accepted. New source-removal IDs contain canonical source and remain under 100 characters. Confirming removal deletes and reschedules only one source.

**Verification:** `uv run pytest tests/test_interaction_handler.py tests/test_config_command.py`

- [ ] Add failing tests for valid confirm/cancel, malformed IDs, wrong guild/user, expiry, permission denial, exact source deletion, peer-source preservation, legacy reset routing, and maximum custom-ID length.
- [ ] Run the verification command and confirm source-removal tests fail while existing interaction tests establish the baseline.
- [ ] Implement a focused `_handle_config_remove()` route or a shared confirmation parser without weakening validation; pass source to the reschedule helper.
- [ ] Re-run the verification command and confirm new removal and existing reset tests pass.
- [ ] Commit with `✨ feat(config): confirm source push removal`.

## Task 7: Localize And Document The New Configuration Workflow

**Files:**

- Modify `src/bot/i18n/locales/zh-TW.json`
- Modify `src/bot/i18n/locales/en-US.json`
- Modify `src/bot/i18n/locales/zh-CN.json`
- Modify `README.md`
- Add `openspec/changes/redesign-daily-push-mechanism/tasks.md`
- Modify locale/spec tests if existing validation requires explicit assertions

**Why:** Every new option, validation error, settings section, and confirmation must remain usable in all supported locales; operators need migration and configuration examples.

**Impact / Compatibility:** Existing localization keys remain. Add source names, independent push labels, no-source removal error, source removal confirmation/success, and unavailable-day logging only where user-facing text exists.

**Verification:** `uv run pytest tests/test_source_layout_phase56.py tests/test_config_command.py && openspec validate redesign-daily-push-mechanism --strict`

- [ ] Add or update failing locale-parity and documentation assertions for the new command keys/examples.
- [ ] Run the verification command and confirm missing keys/checklist entries fail.
- [ ] Add equivalent keys in all locale JSON files, update README command table/examples/migration note, and mark completed OpenSpec tasks only as implementation evidence is produced.
- [ ] Re-run the verification command and confirm locale tests and strict OpenSpec validation pass.
- [ ] Commit with `📝 docs(config): document multi-source daily pushes`.

## Task 8: Full Regression, Architecture Review, And Completion Evidence

**Files:**

- Modify only files required to fix verified regressions within the approved scope
- Update `docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/` through the workspace helper

**Why:** Cross-module schema and scheduler changes need fresh full-suite evidence and explicit retirement verification.

**Verification:** Run every command in the plan header.

- [ ] Run targeted test groups once more and record exact results.
- [ ] Run full pytest, Ruff check, Ruff format check, strict OpenSpec validation, lingering-reference searches for legacy push columns and server-only job IDs, and Aegis workspace check.
- [ ] Fix only failures caused by this change, re-running the narrow failing command after each fix.
- [ ] Re-run the entire verification set and perform the architecture review: ownership, boundaries, contract, dependency direction, legacy retirement, and complexity closure.
- [ ] Update OpenSpec task checkboxes and Aegis checkpoint/evidence/drift records, then commit final scoped fixes/evidence with repository-history style.

## Risks And Rewind Rules

- If migration cannot prove identity/count preservation, stop and retain the legacy table; do not add fallback reads.
- If Discord option count or custom-ID length exceeds platform limits, simplify confirmation encoding within the existing `/config` owner; do not introduce a second public command without design review.
- If multi-problem rendering requires a new interaction protocol, stop and verify why the existing problem buttons are insufficient.
- If baseline tests fail before relevant edits, record them separately and do not attribute them to this change.
- If any task introduces a fourth source or duplicate same-source push, return to design.

## Retirement

- Retire `channel_id`, `role_id`, `post_time`, and `timezone` from `server_settings` after validated copy.
- Retire `set_server_settings()` and `get_all_servers()` once all internal callers use normalized APIs.
- Retire server-only job ID `daily_challenge_{server_id}` and hard-coded `com` delivery guard keys.
- Retain source-less `/config` as an external compatibility behavior, not as a persistence fallback.
- Retain the migration backup as an operator rollback artifact; never read it on the normal runtime path.
