## ADDED Requirements

### Requirement: Thin bootstrap entrypoint
The bot runtime SHALL centralize startup orchestration inside the `bot` package, and repository-root `bot.py` SHALL only delegate to package bootstrap logic.

#### Scenario: Root launcher delegation
- **WHEN** the bot starts through repository-root `bot.py`
- **THEN** the launcher SHALL delegate to package bootstrap logic under `bot.*` and SHALL NOT retain direct resource initialization, cog discovery, or shutdown orchestration logic

## MODIFIED Requirements

### Requirement: Bot initialization and shared resource lifecycle
The bot SHALL initialize all shared resources through package bootstrap code under `src/bot/` before loading cogs. Shared resources SHALL be attached to the bot instance for cog access via `self.bot.<resource>`, and ordinary package imports SHALL NOT trigger runtime initialization as an import side effect.

#### Scenario: Successful startup
- **WHEN** the bot process starts
- **THEN** package bootstrap code SHALL initialize all shared resources needed by the runtime and attach them to the bot instance before the bot starts serving Discord events

#### Scenario: Cog auto-loading
- **WHEN** startup loads extensions
- **THEN** all supported cog modules discovered under `bot.cogs` SHALL be loaded automatically through canonical extension names in deterministic lexicographic order

#### Scenario: Import side-effect isolation
- **WHEN** a non-bootstrap module under `bot.*` is imported for testing or runtime reuse
- **THEN** the import SHALL NOT create database files, log files, API sessions, Discord bot instances, or other startup side effects

### Requirement: Dynamic cog management
The bot SHALL provide owner-only commands for dynamic cog loading, unloading, and reloading while preserving the existing bare-name operator workflow.

#### Scenario: Bare-name reload
- **WHEN** the bot owner runs the reload command with a bare cog name such as `similar_cog`
- **THEN** the bot SHALL normalize that value to the canonical extension name `bot.cogs.similar_cog` before reloading

#### Scenario: Canonical name stability
- **WHEN** dynamic cog commands receive a cog name that is already canonicalized or malformed
- **THEN** the bot SHALL canonicalize valid bare names exactly once and SHALL reject invalid path-like names instead of constructing ambiguous extension names

### Requirement: Graceful shutdown
The bot SHALL perform cleanup on shutdown, including scheduler shutdown and API client session cleanup, through the package bootstrap lifecycle.

#### Scenario: Bot process exit
- **WHEN** the bot process is terminating
- **THEN** package bootstrap shutdown logic SHALL close shared runtime resources and shut down the scheduler gracefully
