## Why

Post-v2.0.2 behavior has evolved faster than the canonical OpenSpec specs: i18n, locale-aware persistence, `/random` source filtering, tag autocomplete edge cases, and similar-search timeout/dedup semantics are only partially represented in `openspec/specs/`. This change brings the canonical specs back in sync with the implemented and archived behavior so future verification, archiving, and implementation work use the correct contract.

## What Changes

- Add canonical i18n specifications covering locale resolution, translation lookup, locale-file contracts, and slash-command metadata localization.
- Update existing configuration, database, slash-command, Discord UI, interaction, daily-schedule, and LLM specs to describe locale-aware behavior introduced after v2.0.2.
- Clarify `/random` source filtering, `source=all` semantics, tag autocomplete fallback behavior, and upstream random/tag API contracts.
- Clarify similar-search timeout and inflight request deduplication semantics so canonical specs match the intended runtime contract.
- No runtime behavior or public API implementation changes are intended in this change.

## Capabilities

### New Capabilities
- `i18n-service`: Locale resolution, translation lookup, interpolation, fallback behavior, supported-locale validation, and locale-file loading.
- `locale-files`: JSON locale-file structure, key parity expectations, zh-TW source-of-truth behavior, preserved technical labels, and Discord length constraints.
- `command-localization`: Discord slash-command metadata localization using `discord.app_commands.Translator` while preserving stable command names.

### Modified Capabilities
- `configuration`: Add canonical i18n configuration requirements for `default_locale` and `supported_locales`.
- `database-layer`: Update server settings and LLM cache requirements for persisted guild language and locale-aware cache keys.
- `slash-commands`: Add `/config language`, localized command/user-facing responses, `/random source` filtering, and source-aware random behavior.
- `discord-ui`: Require embeds, buttons, footers, and settings displays to resolve user-visible strings through the active locale.
- `interaction-handler`: Require interaction responses and LLM-triggering button flows to use the resolved locale.
- `daily-schedule`: Require scheduled posts without interaction context to resolve locale from guild settings and configuration fallback.
- `llm-integration`: Require locale-aware LLM prompts, output language, and cache separation.
- `tag-autocomplete`: Document `source=all` fallback and source-aware tag suggestion behavior.
- `embedding-search`: Clarify similar-search timeout override and inflight deduplication contract.

## Impact

- Affected specs: `openspec/specs/i18n-service/`, `openspec/specs/locale-files/`, `openspec/specs/command-localization/`, `configuration`, `database-layer`, `slash-commands`, `discord-ui`, `interaction-handler`, `daily-schedule`, `llm-integration`, `tag-autocomplete`, and `embedding-search`.
- Affected implementation areas for traceability only: `src/bot/i18n/`, `src/bot/utils/config.py`, `src/bot/utils/database.py`, `src/bot/cogs/`, `src/bot/llms/`, and `src/bot/api_client.py`.
- No dependency, database migration, or runtime code changes are expected; this is a specification synchronization change.
