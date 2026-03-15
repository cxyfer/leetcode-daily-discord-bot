# source-layout Specification

## Purpose
TBD - created by archiving change reorganize-source-layout. Update Purpose after archive.
## Requirements
### Requirement: Canonical runtime package boundary
The system SHALL treat `src/bot/` as the only canonical runtime source boundary for application code. Runtime modules, cogs, LLM integrations, utility modules, and API integration modules SHALL live under the `bot` package rather than at the repository root.

#### Scenario: Runtime code ownership
- **WHEN** application runtime code is reorganized
- **THEN** the implementation SHALL place runtime modules under `src/bot/` and SHALL NOT treat repository-root modules other than `bot.py` as supported runtime entrypoints

#### Scenario: Package namespace contract
- **WHEN** internal runtime code imports another application module
- **THEN** it SHALL import through the `bot.*` namespace rather than through repository-root module names

### Requirement: Thin root launcher contract
The system SHALL preserve `uv run bot.py` as the formal user-facing launch command, and repository-root `bot.py` SHALL be a thin launcher that delegates into the `bot` package.

#### Scenario: Supported launch command
- **WHEN** an operator starts the bot with `uv run bot.py`
- **THEN** repository-root `bot.py` SHALL make `src/` importable and delegate execution to package bootstrap logic under `bot.*`

#### Scenario: Root-level compatibility boundary
- **WHEN** runtime compatibility exceptions are evaluated after the layout migration
- **THEN** repository-root `bot.py` SHALL be the only supported root-level runtime exception

### Requirement: Package-based cog discovery
The system SHALL discover and manage cogs through the `bot.cogs.*` package namespace instead of through repository-relative filesystem assumptions.

#### Scenario: Startup discovery
- **WHEN** startup loads extensions
- **THEN** the system SHALL enumerate Python modules from the `bot.cogs` package, ignore files whose names start with `_`, and load discovered cogs in deterministic lexicographic filename order

#### Scenario: Canonical extension names
- **WHEN** an internal extension name is constructed for a cog
- **THEN** the canonical extension name SHALL be `bot.cogs.<module_name>`

### Requirement: Repository-root path authority
The system SHALL resolve repository-root assets through a shared path authority so runtime behavior is independent of the current working directory.

#### Scenario: Marker-based root resolution
- **WHEN** runtime code resolves the repository root without an override
- **THEN** it SHALL search upward for `pyproject.toml`, then for `.git`, and use the first matching ancestor as the repository root

#### Scenario: Environment override
- **WHEN** marker-based repository root resolution fails
- **THEN** the system SHALL read `BOT_REPO_ROOT` as an explicit override before failing

#### Scenario: Fail-fast on unresolved root
- **WHEN** neither marker-based detection nor `BOT_REPO_ROOT` can determine the repository root
- **THEN** the system SHALL raise an explicit error instead of silently using the current working directory

### Requirement: Package-oriented test layout
The system SHALL keep `tests/` at the repository root while making tests validate the packaged runtime contract.

#### Scenario: Test import contract
- **WHEN** tests import application code after the layout migration
- **THEN** they SHALL import from `bot.*` and SHALL NOT rely on `sys.path` hacks for repository-root module imports

#### Scenario: Coverage target contract
- **WHEN** automated tests collect coverage for the runtime codebase
- **THEN** coverage SHALL target the packaged runtime code under `src/bot` rather than legacy repository-root module paths

