## ADDED Requirements

### Requirement: Shared default constants
`utils/config.py` SHALL export module-level constants `DEFAULT_POST_TIME = "00:00"` and `DEFAULT_TIMEZONE = "UTC"` as the single source of truth for default scheduling values.

#### Scenario: Import from slash commands cog
- **WHEN** `slash_commands_cog.py` needs the default post time or timezone
- **THEN** it SHALL import `DEFAULT_POST_TIME` / `DEFAULT_TIMEZONE` from `utils.config`

#### Scenario: Import from schedule manager cog
- **WHEN** `schedule_manager_cog.py` needs the default post time or timezone
- **THEN** it SHALL import `DEFAULT_POST_TIME` / `DEFAULT_TIMEZONE` from `utils.config`

#### Scenario: Consistency with ConfigManager
- **WHEN** `ConfigManager.post_time` or `ConfigManager.timezone` properties return their defaults
- **THEN** the default values SHALL be identical to `DEFAULT_POST_TIME` and `DEFAULT_TIMEZONE`

## PBT Properties

### Property: Single source of truth
- **INVARIANT**: `DEFAULT_POST_TIME` and `DEFAULT_TIMEZONE` are defined in exactly one location (`utils/config.py`) and all consumers import from there
- **FALSIFICATION**: grep the codebase for hardcoded `"00:00"` or `"UTC"` used as scheduling defaults outside of `utils/config.py`
