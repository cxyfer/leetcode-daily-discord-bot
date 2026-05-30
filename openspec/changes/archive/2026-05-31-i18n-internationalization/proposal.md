## Why

This bot's entire UI surface — slash command descriptions, error messages, button labels, embed fields, and LLM prompts — is hardcoded in Traditional Chinese (~120+ strings across 6 files). This limits adoption to Chinese-speaking servers. Adding i18n support enables English and Simplified Chinese users to use the bot in their preferred language, expanding the potential user base.

## What Changes

- Introduce a centralized i18n service with JSON translation files for zh-TW, en-US, and zh-CN
- Add per-guild language preference stored in the database, configurable via `/config language`
- Localize all slash command metadata (descriptions, parameter descriptions) using discord.py's built-in Translator
- Replace all hardcoded user-facing strings with translation key lookups
- Localize LLM prompt templates so translation/inspiration output follows the guild's language
- Extend LLM cache schema to include locale in cache keys, preventing cross-language cache pollution
- Add 5-level locale resolution: guild DB → Discord guild_locale → interaction.locale → config default → zh-TW

## Capabilities

### New Capabilities
- `i18n-service`: Core i18n infrastructure — locale resolution, JSON string table loading, `t()` API, fallback chain with logging
- `locale-files`: Translation files (`src/bot/i18n/locales/*.json`) containing all user-facing strings for zh-TW, en-US, zh-CN
- `command-localization`: discord.py `Translator` subclass for slash command metadata localization (name, description, parameter descriptions)

### Modified Capabilities
- `database-layer`: Add `language` column to `server_settings`; add `locale` to LLM cache primary keys (`llm_translate_results`, `llm_inspire_results`)
- `configuration`: Add `i18n.default_locale` and `i18n.supported_locales` to config.toml schema
- `discord-ui`: Replace all hardcoded strings in `ui_helpers.py` and `ui_constants.py` with `t()` calls (embed titles, field names, footers, button labels)
- `interaction-handler`: Replace hardcoded error/confirmation messages with `t()` calls; LLM translate output target follows guild locale
- `slash-commands`: Replace hardcoded validation/error messages with `t()` calls; add `language` parameter to `/config` command with Choice list
- `llm-integration`: Make prompt templates locale-aware (inject `output_language` variable); extend cache keys to include locale
- `daily-schedule`: Scheduled daily challenge posts resolve language from guild DB setting (no interaction context)

## Impact

- **Code changes**: 6 existing files modified, 4 new files created (`src/bot/i18n/`)
- **Database**: Schema migration on `server_settings` (add column), `llm_translate_results` and `llm_inspire_results` (add column + PK change)
- **Dependencies**: No new external dependencies (uses discord.py's built-in Translator + Python stdlib)
- **Breaking changes**: LLM cache will be invalidated for existing entries after schema migration (locale column added to PK)
- **Discord API**: Slash command sync will include localization payloads; no API version change required
