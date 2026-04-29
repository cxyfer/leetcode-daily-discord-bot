# Design: /random Command

## Context

Users need a quick way to get random LeetCode problems for practice beyond daily challenges. The `/random` command will leverage existing OJ API filtering capabilities and reuse established UI components.

**Current State:**
- SlashCommandsCog already handles `/daily`, `/problem`, `/recent`, `/config`
- OjApiClient provides `get_problem()`, `get_daily()`, `resolve()`, `search_similar()`
- UI helpers (`create_problem_embed`, `create_problem_view`) are source-aware and reusable
- InteractionHandlerCog routes button clicks via `problem|{source}|{id}|{action}` format

**Constraints:**
- LeetCode-only for v1 (no multi-source support)
- No local problem cache/index (API provides full filtering)
- Discord 3-second interaction timeout requires `defer()`

## Goals / Non-Goals

**Goals:**
- `/random` command with difficulty, tags, rating_min, rating_max filters
- Reuse existing UI components for consistent display
- Maintain error handling patterns (ApiProcessingError, ApiNetworkError, ApiRateLimitError)
- Clear error messages when no problems match filters

**Non-Goals:**
- Multi-source support (AtCoder, Codeforces, etc.)
- Local problem caching or indexing
- Tag autocomplete (requires additional API support)
- User history exclusion (avoid repeat recommendations)

## Decisions

### Decision 1: Two-Call API Strategy
**Choice:** Bot-side random selection via two API calls (count → random page → fetch item)

**Rationale:**
- OJ API already supports filtered listing with pagination
- No need to modify upstream API
- Minimal code change, reuses existing HTTP client

**Alternatives Considered:**
- Server-side random endpoint: Cleaner but requires upstream API work outside this repo
- Local cached index: Contradicts proposal scope, adds sync complexity
- Random ID probing: Inefficient, fails for sparse IDs and non-ID filters

### Decision 2: Placement in SlashCommandsCog
**Choice:** Add `/random` to existing SlashCommandsCog rather than new cog

**Rationale:**
- `/daily` and `/problem` already live there with same public/ephemeral behavior
- Exception mapping and defer pattern are established
- Consistent with existing architecture

### Decision 3: Rating Parameter Auto-Swap
**Choice:** Automatically swap rating_min and rating_max when min > max

**Rationale:**
- User-friendly: prevents silent zero-result queries
- Follows principle of least surprise
- Simple validation logic

### Decision 4: Filter Summary in Error Messages
**Choice:** Show applied filters in no-result error messages

**Rationale:**
- Helps users understand why no problems matched
- Guides them to adjust filter criteria
- Better UX than generic "no results" message

## Risks / Trade-offs

**Risk 1: Two API calls increase latency and failure probability**
→ Mitigation: Use `defer()` to handle Discord timeout; accept slightly higher latency for filtered random selection

**Risk 2: Race condition between count and page fetch**
→ Mitigation: If selected page returns empty, retry with different random offset (bounded retries)

**Risk 3: OJ API list endpoint response shape not codified in tests**
→ Mitigation: Add contract tests during implementation; document expected response format

**Risk 4: Randomness complicates deterministic testing**
→ Mitigation: Use RNG injection or monkeypatching in tests; log selected random seed for debugging

**Risk 5: Input normalization ambiguity for tags**
→ Mitigation: Pass tags as-is to API (single tag per parameter); document encoding behavior

## Implementation Approach

1. **OjApiClient.get_random_problem()**: New method with two-call strategy
2. **SlashCommandsCog.random_command()**: New command with filter parameters
3. **Error handling**: Reuse existing ApiError mapping
4. **UI rendering**: Reuse create_problem_embed() and create_problem_view()
5. **Testing**: Unit tests for parameter validation, integration tests for API flow
