## ADDED Requirements

### Requirement: Bot initialization and shared resource lifecycle
The bot SHALL initialize all shared resources (LeetCode clients, database managers, LLM models, logger) before loading cogs. Resources SHALL be attached to the bot instance for cog access via `self.bot.<resource>`.

#### Scenario: Successful startup
- **WHEN** the bot process starts
- **THEN** all shared resources (lcus, lccn, db, llm_translate_db, llm_inspire_db, llm, llm_pro, logger) are initialized and attached to the bot instance

#### Scenario: Cog auto-loading
- **WHEN** `load_extensions()` is called during startup
- **THEN** all Python files in the `cogs/` directory SHALL be loaded as cogs automatically

#### Scenario: Button prefix constants
- **WHEN** the bot initializes
- **THEN** button prefix constants (LEETCODE_*_BUTTON_PREFIX) SHALL be attached to the bot instance for cog access

### Requirement: Discord gateway event handling
The bot SHALL handle the `on_ready` event to sync slash commands and initialize schedules.

#### Scenario: Bot becomes ready
- **WHEN** the Discord gateway fires the `on_ready` event
- **THEN** the bot SHALL sync application commands and call `ScheduleManagerCog.initialize_schedules()`

### Requirement: Graceful degradation for optional features
The bot SHALL start successfully even if optional features (LLM, embeddings) are not configured.

#### Scenario: Missing LLM API key
- **WHEN** no LLM API key is configured
- **THEN** the bot SHALL start without LLM features, and LLM-related buttons SHALL be hidden or disabled

### Requirement: Configuration fallback
The bot SHALL support both `config.toml` and `.env` file for configuration, with `config.toml` as the primary source.

#### Scenario: TOML not found
- **WHEN** `config.toml` does not exist but `.env` is present
- **THEN** the bot SHALL load `.env` and use a DummyConfig compatibility wrapper

### Requirement: Discord intents and permissions
The bot SHALL request Message Content intent and require Send Messages, Embed Links, and Use Slash Commands permissions.

#### Scenario: Required permissions
- **WHEN** the bot joins a server
- **THEN** it SHALL function correctly with Send Messages, Embed Links, and Use Slash Commands permissions

### Requirement: Dynamic cog management
The bot SHALL provide owner-only commands for dynamic cog loading, unloading, and reloading.

#### Scenario: Reload cog
- **WHEN** the bot owner runs the reload command with a cog name
- **THEN** the bot SHALL unload and reload the specified cog without restarting

### Requirement: Graceful shutdown
The bot SHALL perform cleanup on shutdown, including scheduler shutdown.

#### Scenario: Bot process exit
- **WHEN** the bot process is terminating
- **THEN** the bot SHALL shut down the scheduler gracefully in the finally block
