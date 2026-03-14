## Context

The repository currently mixes runtime modules, package-like directories, test code, documentation, and operational assets at the repository root. The current startup path in `bot.py` performs configuration loading, database initialization, API client setup, bot construction, and cog discovery using root-relative assumptions such as `./cogs`, while internal modules and tests import root-level modules directly.

This coupling makes the source-layout refactor risky because filesystem layout, import paths, startup behavior, and runtime path resolution are currently intertwined. The change needs a canonical application boundary under `src/bot/` without changing the external launch habit of `uv run bot.py` and without bundling unrelated architectural refactors.

The repository also contains stale embedding-related documentation and spec text. Current runtime behavior already routes `/similar` through `OjApiClient`, while `embedding_cli.py` and `embeddings/` no longer exist. The new layout must preserve the actual remote-backed ownership model rather than reintroducing obsolete local embedding responsibilities.

## Goals / Non-Goals

**Goals:**
- Establish `src/bot/` as the single canonical runtime source boundary.
- Move runtime code into the `bot` package while keeping `api_client.py` and `leetcode.py` as flat core modules.
- Preserve the formal user-facing launch contract `uv run bot.py`.
- Replace root-relative import and cog-loading assumptions with package-oriented contracts rooted at `bot.*` and `bot.cogs.*`.
- Make config and runtime asset resolution independent of current working directory.
- Keep tests at repository root while converting them to package imports.
- Align OpenSpec artifacts and documentation with the actual remote-only ownership of `/similar` and embedding functionality.

**Non-Goals:**
- No deeper domain refactor such as introducing `clients/`, `services/`, or other new architecture layers for `api_client.py` or `leetcode.py`.
- No reintroduction of `embedding_cli.py`, `embeddings/`, or any local embedding pipeline.
- No long-term compatibility support for root-level runtime imports such as `from leetcode import ...` or `from api_client import ...`.
- No change to the user-facing dynamic cog command shape; only the internal extension namespace changes.
- No unrelated feature work, behavior changes to slash commands, or API redesign.

## Decisions

### 1. Use `src/bot/` as the only runtime package boundary
**Decision:** All application runtime code moves under `src/bot/`, including `cogs/`, `llms/`, `utils/`, `api_client.py`, and `leetcode.py`.

**Rationale:** This creates a single explicit ownership boundary for runtime code, removes accidental root imports, and makes the repository package-oriented without mixing code and repo assets at the same level.

**Alternatives considered:**
- Keep runtime modules at repository root: rejected because it preserves the current ambiguity and root-coupled imports.
- Split immediately into deeper domains such as `clients/` and `services/`: rejected because it combines layout migration with semantic refactoring and increases migration risk.

### 2. Keep repo-root `bot.py` as the formal launch contract, but only as a thin entrypoint
**Decision:** `uv run bot.py` remains the supported user-facing command. Repo-root `bot.py` delegates into package bootstrap code under `src/bot/` and must not retain full initialization logic.

**Rationale:** The user explicitly wants to keep `uv run bot.py`. Preserving that contract avoids workflow churn while still allowing the actual runtime implementation to live inside the package boundary.

**Alternatives considered:**
- Switch the formal entrypoint to `python -m bot`: rejected because it breaks the chosen external command contract.
- Keep all bootstrap logic in root `bot.py`: rejected because it would preserve a permanent architectural exception and weaken the value of the new source boundary.

### 3. Standardize internal imports on `bot.*` and drop root-level runtime import compatibility
**Decision:** Internal code and tests import moved modules only through the `bot.*` namespace. Compatibility shims are not provided for root-level runtime imports beyond the root `bot.py` entrypoint.

**Rationale:** Supporting both root imports and package imports risks duplicate module loading, broken singletons, inconsistent monkeypatching, and long-lived migration debt.

**Alternatives considered:**
- Short-term dual import compatibility: rejected because it still introduces duplicate-namespace hazards.
- Permanent dual compatibility: rejected because it formalizes the exact ambiguity this change is meant to remove.

### 4. Replace filesystem-relative cog discovery with package-based discovery rooted at `bot.cogs.*`
**Decision:** Cog discovery, load, unload, reload, and startup use internal extension names in the `bot.cogs.*` namespace. User-facing owner commands continue to accept bare names like `similar_cog`, which are mapped internally to `bot.cogs.similar_cog`.

**Rationale:** The current `./cogs` scan is tied to current working directory and repository layout. Package-based discovery matches the new runtime boundary while preserving the existing operator-facing command ergonomics.

**Alternatives considered:**
- Continue scanning `./cogs`: rejected because it keeps the runtime CWD-sensitive.
- Require full extension paths from operators: rejected because it adds avoidable workflow friction without improving internal correctness.

### 5. Introduce centralized repo-root path resolution with marker detection and optional environment override
**Decision:** Runtime code resolves `config.toml`, `.env`, `data/`, and `logs/` through a shared path authority that discovers repo root from markers such as `pyproject.toml` or `.git`, with an environment variable override for exceptional environments.

**Rationale:** After moving runtime code under `src/`, direct relative paths like `config.toml`, `./logs`, and `data/data.db` become fragile under pytest, IDE runs, Docker, and non-root launch contexts. A single path authority keeps behavior CWD-neutral.

**Alternatives considered:**
- Continue relying on current working directory: rejected because it is the primary source of migration fragility.
- Require environment variables only: rejected because it makes ordinary local development and test execution unnecessarily cumbersome.

### 6. Keep embedding and similarity ownership remote-only
**Decision:** The source-layout change must treat `/similar` as API-backed via `api_client.py`. No local embedding package, CLI, or rebuild/index workflow is recreated.

**Rationale:** Repository evidence shows the runtime already uses `OjApiClient` for `/similar`, while local embedding artifacts are absent. Reintroducing a local pipeline would reopen a resolved product/architecture decision and expand scope beyond layout reorganization.

**Alternatives considered:**
- Restore `embedding_cli.py` and `bot.embeddings`: rejected because it conflicts with current runtime ownership and stale-artifact cleanup goals.
- Preserve ambiguous dual ownership in docs/specs: rejected because it leaves implementation non-mechanical and contradictory.

### 7. Keep tests at repository root but convert them to package-oriented execution
**Decision:** `tests/` remains at the repository root, but tests must mirror the package structure, import from `bot.*`, and stop using `sys.path.insert(...)` for root-module access.

**Rationale:** Keeping tests at top level matches standard Python layout, while package imports validate the actual post-migration contract instead of relying on legacy shortcuts.

**Alternatives considered:**
- Move tests under `src/`: rejected because tests are not runtime code and do not belong inside the application package boundary.
- Preserve path-hack-based tests: rejected because they bypass the package contract and hide migration errors.

## Risks / Trade-offs

- **Root entrypoint retained as a special case** → Mitigation: restrict repo-root `bot.py` to thin delegation only and document it as the single allowed root-level runtime exception.
- **Package migration may expose latent circular imports** → Mitigation: keep module movement minimal-churn, standardize imports in one direction, and avoid semantic refactors during the layout move.
- **Current tests and tooling may silently depend on root imports** → Mitigation: explicitly update pytest/package configuration and test imports as part of the migration contract.
- **Package and script naming may create namespace confusion between `bot.py` and package `bot`** → Mitigation: keep runtime logic in package modules and ensure the root entrypoint only delegates into the package.
- **Stale documentation can preserve obsolete local embedding assumptions** → Mitigation: require docs/OpenSpec cleanup as part of this change rather than as follow-up work.
- **CWD-neutral path resolution can be inconsistently reimplemented across modules** → Mitigation: define one shared path authority and forbid ad hoc `Path.cwd()` or raw relative path assumptions in runtime code.

## Migration Plan

1. Define the canonical runtime layout in specs and this design document.
2. Introduce package-oriented bootstrap structure under `src/bot/` while preserving root `bot.py` as the thin formal entrypoint.
3. Move runtime modules and directories into `src/bot/` with minimal semantic change.
4. Update internal imports to `bot.*` and convert cog discovery/loading to `bot.cogs.*` with bare-name external mapping.
5. Introduce centralized repo-root path resolution and update config/log/data access to use it.
6. Update tests and packaging/test configuration so `bot.*` resolves from `src/` without root-import fallbacks.
7. Remove stale OpenSpec/docs references to local embedding workflows and describe `/similar` as remote-only.
8. Verify that `uv run bot.py` remains the stable launch command and that runtime behavior is independent of current working directory.

**Rollback strategy:** If migration fails during implementation, restore the previous root-based import and module layout from version control as one unit. Because this is a source-layout change, partial rollback is undesirable; rollback should revert the layout and import contract together.

## Open Questions

None. The remaining planning decisions have been resolved for this change, and implementation should proceed mechanically from the approved constraints.
