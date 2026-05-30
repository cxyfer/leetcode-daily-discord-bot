## Context

The bot currently implements `/random` through client-side selection: it fetches the total count of matching LeetCode problems, picks a page locally, then fetches one problem. Upstream `oj-api-rs` now exposes a native `GET /api/v1/random` endpoint that accepts the same filter dimensions needed by the bot and returns a `results` array of problem details.

The change is isolated to the API client layer and the `/random` command path. The Discord command surface does not need to change, but the bot must continue to behave the same for users: filters stay the same, `rating_min > rating_max` normalization stays the same, and the bot-facing method still returns one problem or `None`.

## Goals / Non-Goals

**Goals:**
- Replace the two-call random selection flow with a single upstream random endpoint call
- Preserve existing `/random` command inputs and visible behavior
- Keep `OjApiClient.get_random_problem()` compatible with current callers by returning one problem or `None`
- Continue handling empty-result cases and API errors through the existing error model
- Keep implementation small and localized to the API client and its tests

**Non-Goals:**
- Add new `/random` command parameters
- Change Discord command descriptions or UI components
- Implement fallback logic across multiple upstream API versions
- Add batch-problem fetch optimization in this change

## Decisions

### D1: Use the upstream native random endpoint directly

**Decision**: Replace the current two-step client-side selection with a single `GET /api/v1/random` request.

**Rationale**: The upstream endpoint already performs the random selection and supports the same filter dimensions the bot needs. Using it removes extra round trips, avoids TOCTOU issues between count and fetch, and removes the LeetCode-only assumption from the client logic.

**Alternatives considered**:
- Keep the current two-call implementation: works today, but duplicates server logic and remains slower and less reliable.
- Add fallback to the old path: increases code complexity and hides upstream deployment mismatches instead of surfacing them.

### D2: Preserve the bot-facing method contract

**Decision**: Keep `get_random_problem()` returning a single problem dictionary or `None`, even though the upstream endpoint returns `{results: [...]}`.

**Rationale**: This keeps the `/random` command and any future callers unchanged. The method only needs to adapt response parsing internally.

**Alternatives considered**:
- Return the raw upstream response: would leak transport details into command code and require broader changes.
- Change the command to consume `results[0]` directly: spreads endpoint-specific parsing outside the API layer.

### D3: Keep existing filter normalization behavior

**Decision**: Preserve current input normalization, including swapping `rating_min` and `rating_max` when they are reversed and omitting unset parameters.

**Rationale**: This keeps user experience stable and ensures the new endpoint receives a clean, minimal query payload.

**Alternatives considered**:
- Push all validation into the upstream API: would make the bot less friendly when users enter inverted ranges.
- Change the command contract now: unnecessary for this compatibility update.

### D4: Treat upstream support as a deployment dependency, not an in-code fallback

**Decision**: Assume the deployed upstream API already supports `GET /api/v1/random` and do not silently fall back to the old implementation.

**Rationale**: The research shows the upstream contract changed intentionally. A silent fallback could mask deployment drift and make failures harder to diagnose.

**Alternatives considered**:
- Dual-path compatibility layer: safer in mixed deployments, but it adds complexity and weakens observability of mismatched versions.

## Risks / Trade-offs

- [Upstream version mismatch] → If the API server is older than the native random endpoint, `/random` will fail until the bot and API are deployed together.
- [Response shape mismatch] → If upstream changes `results` or item shape, parsing may fail; mitigate with focused tests around `results[0]` handling and empty-response behavior.
- [Filter semantics drift] → If upstream interprets difficulty or tag filters differently, user-visible results may shift; mitigate by preserving the current query normalization and adding tests that verify request payloads.
- [Reduced client-side control] → The bot no longer owns random selection logic; mitigate by keeping the method contract stable so command code stays simple.

## Migration Plan

1. Update `OjApiClient.get_random_problem()` to call `GET /api/v1/random` with the existing filter parameters and `count=1`.
2. Parse the upstream response by returning the first entry in `results`, or `None` when no results are returned.
3. Update tests to validate the request payload, response parsing, and zero-result behavior.
4. Deploy the bot together with an upstream API version that includes the native random endpoint.
5. If rollback is needed, restore the old two-call implementation in the client and redeploy both services in sync.

## Open Questions

- None for this change. The required behavior is already described by the upstream research and the current `slash-commands` spec.
