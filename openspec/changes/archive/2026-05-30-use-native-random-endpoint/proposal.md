## Why

The bot's `/random` implementation still performs client-side random selection with two LeetCode API calls. Upstream `oj-api-rs` now provides a native `/api/v1/random` endpoint, which reduces round trips, removes the LeetCode-only limitation, and avoids race conditions between count fetch and page fetch.

## What Changes

- Replace the current two-call random selection flow with a single call to the upstream native random endpoint
- Keep the `/random` Discord command surface unchanged for users
- Preserve existing filter behavior for difficulty, tags, and rating range
- Continue normalizing `rating_min > rating_max` before sending the request
- Keep the bot-facing `get_random_problem()` contract the same by returning the first problem or `None`
- **BREAKING**: the bot now depends on the upstream API server supporting `GET /api/v1/random`

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `slash-commands`: the API client random problem method SHALL fetch random problems through the upstream native `/random` endpoint instead of performing client-side two-call selection

## Impact

- **Code**: `src/bot/api_client.py` needs to switch `get_random_problem()` to the native random endpoint
- **Tests**: update or add tests for the new request shape, response parsing, and no-match behavior
- **API dependency**: requires an upstream `oj-api-rs` deployment that supports `GET /api/v1/random`
- **User-facing behavior**: `/random` should behave the same from Discord, but with lower latency and broader source support behind the scenes
