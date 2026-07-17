## Why

The bot currently exposes only LeetCode daily challenges even though the configured oj-api-rs backend can return `sheep` and `0x3f` daily sources, including ordered multi-problem responses. A dedicated manual command is needed so users can query those sources without changing the existing `/daily`, `/daily_cn`, or scheduled-delivery behavior.

## What Changes

- Add a manual `/daily_extra` slash command with required `source` choices `sheep` and `0x3f`, plus optional `date` and `public` parameters.
- Preserve the complete upstream `{date, source, problems}` envelope for additional daily sources.
- Render a single returned problem as a full problem card; render multiple returned problems as an ordered overview with one existing unified problem-detail button per problem.
- Keep each detail opened from the overview private to the clicking user, even when the initial overview is public.
- Reject payloads that cannot be represented completely within Discord's 25-button and stable custom-id limits instead of attaching a partial view.
- Scope daily payload reuse by request target and date so LeetCode domains, `sheep`, and `0x3f` cannot collide in the in-flight or short-lived cache.
- Add localized command metadata and user-facing success/error text for all supported locales.
- Preserve existing `/daily`, `/daily_cn`, oj-api-rs v0.4 LeetCode compatibility, and scheduled posting behavior.
- No database, scheduler, configuration, or external dependency changes.

## Capabilities

### New Capabilities

- `daily-extra-command`: Defines manual additional-source retrieval, single- and multi-problem presentation, private detail interactions, localization, validation, and upstream error handling.

### Modified Capabilities

- `daily-request-deduplication`: Generalizes daily payload reuse from LeetCode domain/date keys to collision-free daily request target/date keys while retaining independent localized rendering.

## Impact

- Affected code and documentation: `src/bot/api_client.py`, `src/bot/cogs/slash_commands_cog.py`, `src/bot/utils/ui_helpers.py`, `src/bot/utils/ui_constants.py`, locale JSON files under `src/bot/i18n/locales/`, and `README.md`.
- Reused interaction contract: `problem|{source}|{problem_id}|view` in `src/bot/cogs/interaction_handler_cog.py`; no new button protocol or interaction state store is introduced.
- Affected tests: API daily query/envelope tests, daily payload reuse tests, slash-command tests, overview safety tests, interaction privacy regression tests, and locale parity tests.
- Upstream dependency: oj-api-rs `GET /api/v1/daily?source={sheep|0x3f}&date={YYYY-MM-DD}` and its existing `200`, `202`, `400`, and `404` behavior.
