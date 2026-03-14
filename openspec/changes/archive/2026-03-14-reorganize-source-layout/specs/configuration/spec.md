## ADDED Requirements

### Requirement: Repository-root path authority
The configuration and runtime support layers SHALL share a single repository-root path authority for resolving configuration files, environment files, databases, and logs.

#### Scenario: Config file resolution
- **WHEN** the system resolves `config.toml`
- **THEN** it SHALL resolve the file relative to the repository root determined by the shared path authority rather than relative to the current working directory

#### Scenario: Runtime asset resolution
- **WHEN** the system resolves `.env`, `data/`, or `logs/`
- **THEN** it SHALL resolve those paths relative to the repository root determined by the shared path authority rather than relative to the current working directory

## MODIFIED Requirements

### Requirement: TOML-based configuration
The system SHALL load configuration from the repository-root `config.toml` as the primary source. When `config.toml` does not exist, the system SHALL fall back to the repository-root `.env` file with a compatibility wrapper, and both lookup paths SHALL be determined by the shared repository-root path authority.

#### Scenario: TOML loading
- **WHEN** the bot starts and repository-root `config.toml` exists
- **THEN** the system SHALL load configuration from that file regardless of the process current working directory

#### Scenario: Environment variable override
- **WHEN** an environment variable is set (for example `DISCORD_TOKEN`)
- **THEN** it SHALL take precedence over the corresponding TOML value

#### Scenario: .env fallback
- **WHEN** repository-root `config.toml` does not exist but repository-root `.env` is present
- **THEN** the system SHALL load `.env` and use a compatibility wrapper without relying on raw relative paths

### Requirement: Lazy singleton pattern
The ConfigManager SHALL use a lazy singleton pattern, initializing only on first access, and path resolution during initialization SHALL be current-working-directory independent.

#### Scenario: First access
- **WHEN** the config is accessed for the first time
- **THEN** the system SHALL resolve the repository root through the shared path authority, parse the repository-root configuration source, and cache the result

#### Scenario: Subsequent access
- **WHEN** the config is accessed again
- **THEN** the system SHALL return the cached configuration without re-parsing or re-evaluating path resolution
