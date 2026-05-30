## 1. Infrastructure Setup

- [x] 1.1 Create `src/bot/i18n/` module structure (`__init__.py`, `service.py`, `translator.py`, `locales/` directory)
- [x] 1.2 Create `zh-TW.json` locale file with all translation keys from existing hardcoded strings
- [x] 1.3 Create `en-US.json` locale file with English translations for all keys
- [x] 1.4 Create `zh-CN.json` locale file with Simplified Chinese translations for all keys
- [x] 1.5 Implement `I18nService` class: `load_locales()`, `t(key, locale, **params)`, `maybe_t(key, locale)`, `resolve_locale(guild_id, guild_locale, interaction_locale)`
- [x] 1.6 Implement `I18nService` fallback logic: target locale → zh-TW → raw key (with warning/error logging)
- [x] 1.7 Implement locale file validation: check key parity across all locale files at startup

## 2. Database Migration

- [x] 2.1 Add `language TEXT NOT NULL DEFAULT 'zh-TW'` column to `server_settings` table via `ALTER TABLE` with existence check
- [x] 2.2 Update `get_server_settings()` to include `language` in SELECT and return dict
- [x] 2.3 Update `set_server_settings()` to accept and persist `language` parameter
- [x] 2.4 Update `get_all_servers()` to include `language` in SELECT
- [x] 2.5 Add `locale TEXT NOT NULL DEFAULT 'zh-TW'` to `llm_translate_results` PK (drop + recreate table)
- [x] 2.6 Add `locale TEXT NOT NULL DEFAULT 'zh-TW'` to `llm_inspire_results` PK (drop + recreate table)
- [x] 2.7 Update `LLMTranslateDatabaseManager` methods (`get_translation`, `save_translation`) to include `locale` parameter
- [x] 2.8 Update `LLMInspireDatabaseManager` methods (`get_inspire`, `save_inspire`) to include `locale` parameter

## 3. Configuration Extension

- [x] 3.1 Add `i18n.default_locale` and `i18n.supported_locales` to config.toml.example
- [x] 3.2 Add `default_locale` and `supported_locales` properties to `ConfigManager`
- [x] 3.3 Pass i18n config to `I18nService` at initialization

## 4. Discord.py Translator

- [x] 4.1 Implement `BotTranslator(discord.app_commands.Translator)` subclass in `src/bot/i18n/translator.py`
- [x] 4.2 Implement `translate()` method reading from `commands` namespace in locale files
- [x] 4.3 Register translator via `bot.tree.set_translator()` in `app.py` BEFORE `tree.sync()`
- [x] 4.4 Add command description keys to all 3 locale files (6 commands × description + ~30 parameter descriptions)

## 5. Runtime String Migration — Error Messages

- [x] 5.1 Add `errors.api.*` keys to locale files (processing, network, rate_limit, generic)
- [x] 5.2 Create shared `send_api_error(interaction, error_kind, locale)` helper replacing duplicated error handling
- [x] 5.3 Replace API error handling in `slash_commands_cog.py` with `t()` calls
- [x] 5.4 Replace API error handling in `interaction_handler_cog.py` with `t()` calls
- [x] 5.5 Replace API error handling in `similar_cog.py` with `t()` calls
- [x] 5.6 Replace API error handling in `ui_helpers.py` with `t()` calls

## 6. Runtime String Migration — Validation Messages

- [x] 6.1 Add `errors.validation.*` keys to locale files (date_format, not_found_for_date, domain_invalid, title_too_long, etc.)
- [x] 6.2 Replace validation error messages in `slash_commands_cog.py` with `t()` calls
- [x] 6.3 Add `errors.config.*` keys to locale files (not_configured, already_reset, first_setup_required, permission_denied, dm_restricted)
- [x] 6.4 Replace config-related error messages in `slash_commands_cog.py` with `t()` calls
- [x] 6.5 Add `errors.reset.*` keys to locale files (invalid_action, wrong_user, expired, cancelled, permission_denied, error, success)
- [x] 6.6 Replace config reset messages in `interaction_handler_cog.py` with `t()` calls

## 7. Runtime String Migration — UI Components

- [x] 7.1 Add `ui.buttons.*` keys to locale files (description, translate, inspire, similar, confirm_reset, cancel)
- [x] 7.8 Replace button labels in `ui_helpers.py` with `t()` calls
- [x] 7.9 Replace button labels in `slash_commands_cog.py` (config reset confirm/cancel) with `t()` calls
- [x] 7.10 Add `ui.embed.*` keys to locale files (similar_title, rewritten_search, base_problem, results, source, difficulty, rating, ac_rate, tags, similar_questions, history_problems, daily_footer, problem_footer, etc.)
- [x] 7.11 Replace embed field names in `ui_helpers.py` with `t()` calls
- [x] 7.12 Add `ui.settings.*` keys to locale files (title, channel, role, time, not_set)
- [x] 7.13 Replace settings embed strings in `ui_helpers.py` with `t()` calls
- [x] 7.14 Add `ui.inspire.*` keys to locale files (title, thinking, traps, algorithms, inspiration)
- [x] 7.15 Replace inspiration field labels in `ui_constants.py` and `ui_helpers.py` with `t()` calls

## 8. Runtime String Migration — LLM Messages

- [x] 8.1 Add `llm.*` keys to locale files (processing_request, translation_not_enabled, inspire_not_enabled, cannot_fetch_description, cannot_fetch_info, cannot_fetch_content, problem_not_found, no_description, content_truncated, translation_truncated, provided_by_model, inspired_by_model)
- [x] 8.2 Replace LLM-related messages in `interaction_handler_cog.py` with `t()` calls
- [x] 8.3 Update LLM translate target language to follow guild locale (replace hardcoded "zh-TW")

## 9. LLM Prompt Template Localization

- [x] 9.1 Add `llm.prompts.*` keys to locale files (translation_system, inspire_system, output_language_names)
- [x] 9.2 Refactor `templates.py` to accept `{output_language}` variable instead of hardcoded Chinese
- [x] 9.3 Update `LLMBase.translate()` to inject target language name into prompt
- [x] 9.4 Update `LLMBase.inspire()` to inject output language name into prompt

## 10. /config language Command

- [x] 10.1 Add `language` parameter to `/config` command with `app_commands.Choice` list (zh-TW, en-US, zh-CN)
- [x] 10.2 Add `commands.config.language.*` keys to locale files (description, current, updated)
- [x] 10.3 Update `create_settings_embed()` to display current language setting
- [x] 10.4 Update `/config` help/description text in locale files

## 11. Daily Schedule Localization

- [x] 11.1 Update `schedule_manager_cog.py` to resolve guild locale from DB when firing scheduled posts
- [x] 11.2 Pass resolved locale to `send_daily_challenge()` for localized embed/view creation
- [x] 11.3 Ensure `send_daily_challenge()` in `ui_helpers.py` accepts and uses locale parameter

## 12. Integration Wiring

- [x] 12.1 Initialize `I18nService` in `bootstrap.py` or `app.py` and attach to bot instance
- [x] 12.2 Update `create_bot_runtime()` to accept and pass i18n service
- [x] 12.3 Pass locale through interaction handlers: extract `interaction.locale` and `interaction.guild_locale` at handler entry points
- [x] 12.4 Update all `create_*_embed()` and `create_*_view()` functions to accept `locale` parameter
