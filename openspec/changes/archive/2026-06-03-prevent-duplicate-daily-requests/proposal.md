## Why

Concurrent `/daily` invocations and clustered scheduled daily jobs can duplicate upstream daily challenge work and, in scheduled flows, risk overlapping delivery for the same server. This is especially visible when many servers fire daily jobs at the same configured minute or when users repeatedly request the same daily challenge.

## What Changes

- Tighten scheduled daily job execution so a server's daily job does not overlap with a previous run.
- Add duplicate prevention for scheduled daily delivery keyed by server/channel/domain/date so one server does not send the same scheduled daily challenge concurrently.
- Add short-lived daily challenge payload reuse so repeated daily challenge rendering can share fetched challenge and history data without changing localized embed generation.
- Preserve manual `/daily` behavior: users can still request current or date-specific daily challenges, with any duplicate suppression limited to concurrent in-flight work and not a persistent block.
- No breaking changes.

## Capabilities

### New Capabilities
- `daily-request-deduplication`: Prevent duplicate in-flight daily challenge work and scheduled delivery while preserving expected manual command behavior.

### Modified Capabilities
- `daily-schedule`: Scheduled daily jobs must avoid overlapping per-server execution and duplicate same-day scheduled delivery.
- `slash-commands`: Daily slash commands should reuse in-flight or cached daily data where possible without suppressing valid user responses.

## Impact

- Affected code: `src/bot/cogs/schedule_manager_cog.py`, `src/bot/cogs/slash_commands_cog.py`, `src/bot/utils/ui_helpers.py`, and possibly `src/bot/api_client.py` or a small daily-service helper.
- Affected behavior: scheduled daily challenge execution, concurrent `/daily` handling, daily challenge/history fetch reuse.
- Dependencies: no new external runtime dependency is expected; implementation should use existing `asyncio`, APScheduler, and in-memory cache patterns.
- Testing: add or update async unit tests for scheduler defaults, duplicate scheduled delivery guard, and daily payload reuse.