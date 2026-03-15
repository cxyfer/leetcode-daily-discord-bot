## 1. Bootstrap package contract

- [x] 1.1 Create the `src/bot/` package skeleton and add side-effect-free `__init__.py` files for `bot`, `bot.cogs`, `bot.llms`, and `bot.utils`
- [x] 1.2 Extract startup orchestration from repository-root `bot.py` into package bootstrap code under `src/bot/`
- [x] 1.3 Reduce repository-root `bot.py` to the thin launcher that makes `src/` importable and delegates to the package bootstrap entrypoint

## 2. Shared path authority

- [x] 2.1 Add a shared repository-root path authority with `pyproject.toml` detection, `.git` fallback, `BOT_REPO_ROOT` override, and fail-fast error behavior
- [x] 2.2 Update configuration loading and `.env` fallback to resolve files through the shared path authority instead of raw relative paths
- [x] 2.3 Update logger and database path handling so `logs/` and `data/` are resolved from the repository root instead of the current working directory

## 3. Runtime module migration

- [x] 3.1 Move `api_client.py`, `leetcode.py`, `llms/`, `utils/`, and `cogs/` into `src/bot/` with minimal semantic change
- [x] 3.2 Rewrite internal runtime imports to use `bot.*` exclusively and remove `sys.path` mutation / repository-root import fallbacks
- [x] 3.3 Keep `api_client.py` and `leetcode.py` as flat core modules under `src/bot/` rather than combining this move with deeper architectural refactors

## 4. Cog discovery and extension management

- [x] 4.1 Replace `./cogs` filesystem scanning with package-based discovery rooted at `bot.cogs` using deterministic lexicographic filename ordering
- [x] 4.2 Update owner `load`, `unload`, and `reload` commands to normalize bare cog names to canonical `bot.cogs.<name>` extension names
- [x] 4.3 Reject malformed or path-like extension names instead of constructing ambiguous extension paths during dynamic cog management

## 5. Test and tooling contract

- [x] 5.1 Update pytest/import configuration so tests resolve `bot.*` from `src/` without repository-root `sys.path` hacks
- [x] 5.2 Convert existing tests to package imports and remove manual `sys.path.insert(...)` / `sys.path.append(...)` usage
- [x] 5.3 Retarget coverage and related tooling to the packaged runtime under `src/bot` instead of legacy repository-root module paths

## 6. Similarity ownership and documentation cleanup

- [x] 6.1 Preserve `/similar` as a remote-only API-backed feature owned by `bot.api_client` and `bot.cogs.similar_cog`
- [x] 6.2 Remove stale embedding pipeline references from OpenSpec/docs/runtime guidance instead of recreating `embedding_cli.py`, `embeddings/`, or local vector workflows
- [x] 6.3 Update Docker, compose, README, and CLAUDE guidance so the documented runtime contract matches the new packaged layout and root-launcher behavior

## 7. End-to-end validation

- [x] 7.1 Verify `uv run bot.py` still launches the bot through the thin root launcher contract
- [x] 7.2 Verify configuration, database, and logging paths resolve to the same repository-root locations from different current working directories
- [x] 7.3 Verify cog discovery order and canonical extension naming remain deterministic across startup and owner commands
- [x] 7.4 Verify the test suite runs against `bot.*` imports without repository-root path hacks
- [x] 7.5 Verify no local embedding pipeline or local similarity index workflow is reintroduced during the source-layout migration
