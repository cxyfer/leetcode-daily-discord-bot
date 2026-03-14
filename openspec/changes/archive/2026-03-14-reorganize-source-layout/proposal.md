## Why

The current bot codebase mixes runtime modules, package directories, and repository assets at the root, which makes source-layout cleanup risky because imports, cog discovery, test loading, and runtime paths are all coupled to the current directory structure. This change is needed now to establish an explicit source-layout contract before any refactor moves application code under `src/` and turns the preferred structure into a maintainable, package-friendly baseline.

## What Changes

- Define a canonical application source boundary under `src/bot/` for bot runtime code, including the currently root-level `api_client.py` and the packaged similarity feature.
- Establish the supported entrypoint, module import contract, and cog discovery contract for the reorganized layout.
- Preserve repo-root/container-root semantics for `config.toml`, `.env`, `data/`, and `logs/` while decoupling runtime code from root-only import assumptions.
- Clarify how `tests/` maps to the reorganized `src/` tree so the developer workflow remains explicit and package-oriented.
- Remove stale local embedding workflow assumptions so `/similar` remains documented as a remote API-backed feature.

## Capabilities

### New Capabilities
- `source-layout`: Define the canonical `src/bot` application structure, module ownership, supported entrypoint, import conventions, and `tests/` to `src/` relationship for the bot codebase.

### Modified Capabilities
- `bot-core`: Update startup and cog-loading requirements so bot initialization works against the canonical packaged layout instead of relying on root-level `cogs/` assumptions.
- `configuration`: Clarify that configuration, environment fallback, database paths, and log paths remain anchored to the repository/container root even when runtime code moves under `src/bot/`.
- `embedding-search`: Clarify the remote API-backed ownership of `/similar` within the reorganized packaged runtime.

## Impact

- Affected code: bot entrypoint, cog loading, `api_client.py`, `leetcode.py`, `llms/`, `utils/`, `/similar` runtime ownership, and test imports.
- Affected tooling: `pyproject.toml`, pytest import/discovery assumptions, package layout conventions, and developer run commands.
- Affected operations: Dockerfile, docker-compose volume expectations, README/CLAUDE.md startup guidance, and repo-root path semantics for config/data/logs.
- Key risk areas: stale embedding documentation/CLI references, root-import compatibility, and CWD-sensitive runtime path assumptions.
