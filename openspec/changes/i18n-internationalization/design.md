## Context

The LeetCode Daily Discord Bot has ~120+ hardcoded Traditional Chinese strings spread across 6 source files (`slash_commands_cog.py`, `interaction_handler_cog.py`, `ui_helpers.py`, `ui_constants.py`, `similar_cog.py`, `templates.py`). There is no i18n infrastructure — no locale files, no translation keys, no language preference storage.

The bot uses discord.py 2.5.2, Python 3.10+, SQLite for persistence, and TOML+env for configuration. Slash commands are registered via `bot.tree.sync()` with no Translator installed.

The goal is to add full i18n support for zh-TW (default), en-US, and zh-CN, with per-guild language configuration.

## Goals / Non-Goals

**Goals:**
- All user-facing strings (errors, embeds, buttons, command descriptions) are translatable via JSON string tables
- Per-guild language preference stored in database, configurable via `/config language`
- Slash command metadata localized via discord.py's built-in Translator system
- LLM translation/inspiration output follows guild language setting
- 5-level locale resolution with graceful fallback
- No new external dependencies

**Non-Goals:**
- Per-user language preference (may add later, out of scope for v1)
- Dynamic language switching mid-conversation
- Translator UI for non-developers (translations maintained in JSON files by developers)
- Localization of Luogu difficulty labels (platform-specific API data, not translatable)
- Localization of LeetCode problem content (source data, handled by LLM translate button)

## Decisions

### D1: Two-Layer Architecture

**Decision**: Split i18n into two independent layers:
1. **discord.py Translator** — handles slash command metadata (name, description, parameter descriptions) via Discord's native localization API
2. **I18nService** — handles runtime strings (errors, embeds, buttons, LLM prompts) via JSON string table lookup

**Rationale**: Discord command metadata and runtime messages have different lifecycle and resolution mechanisms. Command localizations are sent once during `tree.sync()` and rendered by Discord client based on user's locale. Runtime strings are resolved per-interaction at send time. Combining them would create unnecessary coupling.

**Alternatives considered**:
- Single gettext-based system: Cannot handle Discord command metadata (discord.py has its own Translator protocol). Would require patching discord.py internals.
- discord.py Translator for everything: Only works for command metadata, not for followup messages, embeds, or error strings.

### D2: JSON String Tables (Not gettext)

**Decision**: Use JSON files for translation strings with a thin `I18nService` wrapper.

**Rationale**:
- The project already uses TOML for config; JSON is equally readable and has better editor/tooling support for i18n
- gettext requires `.po/.mo` compilation step, adds complexity for a small project with ~120 strings
- JSON allows nested key structure (`errors.api.processing`) which is more organized than flat gettext msgids
- If the project scales to 5+ languages or needs plural rules, migration to gettext is straightforward

**File structure**:
```
src/bot/i18n/
├── __init__.py
├── service.py          # I18nService: load, t(), resolve_locale()
├── translator.py       # discord.py Translator subclass
└── locales/
    ├── zh-TW.json
    ├── en-US.json
    └── zh-CN.json
```

### D3: 5-Level Locale Resolution

**Decision**: Resolve locale with the following priority chain:

```
1. guild DB setting       ← /config language (explicit admin choice)
2. discord guild_locale   ← Discord server's preferred locale (free signal)
3. interaction.locale     ← User's Discord client language
4. config default_locale  ← config.toml global default
5. "zh-TW"                ← Hard fallback
```

**Rationale**:
- Guild DB setting is highest because it's an explicit admin decision
- `guild_locale` is a free signal from Discord that represents the server community's language — most servers don't need to configure anything
- `interaction.locale` catches DM scenarios and guilds without Discord locale set
- Config default provides deployment-level control
- Hard fallback ensures the bot never returns empty strings

**Special cases**:
- Scheduled daily posts (no interaction): levels 1 → 4 → 5 only
- DM messages (no guild): levels 3 → 4 → 5 only

### D4: Database Schema Changes

**Decision**: Add `language TEXT NOT NULL DEFAULT 'zh-TW'` to `server_settings`. Add `locale TEXT NOT NULL DEFAULT 'zh-TW'` to LLM cache tables' primary keys.

**Migration strategy**:
- Use `ALTER TABLE ... ADD COLUMN` at startup (SQLite supports this)
- Check column existence via `PRAGMA table_info()` before altering
- Existing rows get the default value automatically
- LLM cache tables: drop and recreate (cache is ephemeral, 7-day expiry)

**LLM cache schema change**:
```sql
-- llm_translate_results: PK changes from (source, problem_id) to (source, problem_id, locale)
-- llm_inspire_results: PK changes from (source, problem_id) to (source, problem_id, locale)
```

### D5: Missing Key Behavior

**Decision**: When a translation key is missing in the target locale:
1. Fall back to zh-TW (default locale)
2. Log a warning: `logger.warning(f"Missing i18n key '{key}' for locale '{locale}', falling back to zh-TW")`
3. If also missing in zh-TW, log error and return the raw key name

**Rationale**: Users always see content (never empty strings). Developers get actionable log messages to find missing translations. Raw key as last resort makes missing translations obvious during development.

### D6: Existing English Field Names

**Decision**: Keep existing English field names (Difficulty, Tags, Results, Source, AC Rate, Rating) as-is in zh-TW locale file.

**Rationale**: LeetCode users are accustomed to English technical terms. Translating these would reduce readability for the target audience. The zh-TW locale file will contain these English strings, and en-US/zh-CN can use the same values or localize as appropriate.

### D7: LLM Prompt Template Strategy

**Decision**: Make prompt templates locale-aware by injecting `output_language` variable into templates.

**Current**: `INSPIRE_JSON_PROMPT_TEMPLATE` hardcodes "僅能使用繁體中文回答"
**After**: Template contains `{output_language}` placeholder, filled with the guild's language name (e.g., "繁體中文", "English", "简体中文")

**Cache key change**: LLM cache primary key includes locale, so the same problem in different languages gets separate cache entries.

### D8: `/config language` Command

**Decision**: Add `language` parameter to existing `/config` command using `app_commands.Choice` list (zh-TW, en-US, zh-CN).

**Rationale**: Reuses existing `/config` command pattern. Choice list prevents invalid input. No new command needed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Slash command rename breaks routing | Keep command `name` in English/ASCII; only localize `description` and parameter descriptions |
| LLM cache invalidation on migration | Acceptable — cache is 7-day TTL, will repopulate naturally |
| English translations longer than Chinese, may hit Discord length limits | Validate all translations against Discord limits (button ≤ 80 chars, embed title ≤ 256 chars, command description ≤ 100 chars) during locale file creation |
| Locale inconsistency (command shows English, response shows Chinese) | 5-level resolution ensures consistent locale within a single interaction |
| Missing translations degrade UX | Fallback to zh-TW + log warning; raw key as last resort |
| `interaction.guild_locale` may be None for some servers | Handled in fallback chain — falls through to interaction.locale or config default |
