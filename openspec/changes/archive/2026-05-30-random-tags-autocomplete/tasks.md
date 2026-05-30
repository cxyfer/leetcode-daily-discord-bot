## 1. API Client — Tags fetching

- [x] 1.1 Add `get_tags(source)` method to `OjApiClient` that calls `GET /api/v1/tags/{source}` and returns `list[str]`
- [x] 1.2 Add `_tags_cache: dict[str, tuple[float, list[str]]]` and `_TAGS_CACHE_TTL = 86400` to `OjApiClient`
- [x] 1.3 Add `get_tags_cached(source)` method with TTL check, cache miss → API call → cache write, and stale fallback on error

## 2. Autocomplete Callback

- [x] 2.1 Add `@random_command.autocomplete("tags")` callback in `SlashCommandsCog`
- [x] 2.2 Read current source from `interaction.namespace.source` (default `"leetcode"`) in the callback
- [x] 2.3 Filter tags by `current` input (case-insensitive substring) and return up to 25 `Choice` objects

## 3. Startup Preloading

- [x] 3.1 In `on_ready` (app.py), fire-and-forget `get_tags_cached()` for `["leetcode", "codeforces"]` via `asyncio.create_task`
- [x] 3.2 Ensure preload failures are logged at warning level and do not block startup

## 4. Tests

- [x] 4.1 Test `get_tags()` returns tag list on 200, empty list on 400/404, propagates error on 500/network failure
- [x] 4.2 Test `get_tags_cached()`: cache hit skips API, cache miss calls API, expired cache refreshes, stale fallback on refresh failure
- [x] 4.3 Test autocomplete callback returns filtered choices for valid source, empty list on API failure, defaults to leetcode when source unset
