## Context

Upstream `oj-api-rs` changed the text-based similar-search contract from GET query parameters to a POST JSON body. The current bot already routes `/similar` text queries through `OjApiClient.search_similar_by_text()`, so the change is isolated to the API client boundary and should not alter the Discord command surface.

The existing code already distinguishes text-query search from problem-id search, and the result rendering path is shared. That makes this a small compatibility update rather than a broader feature change.

## Goals / Non-Goals

**Goals:**
- Align text-query similarity requests with the upstream POST contract.
- Preserve the existing `/similar` command UX and problem-id path.
- Keep the change narrowly scoped to the API client and tests.

**Non-Goals:**
- Do not change the `/similar` command parameters or public response format.
- Do not add a compatibility fallback unless required by deployment reality.
- Do not redesign similarity result rendering or detail-button behavior.

## Decisions

- Use `POST /similar` with a JSON body for text queries.
  - Rationale: matches the upstream contract and avoids URL truncation / encoding issues for long text queries.
  - Alternative considered: keep GET and add a server-side compatibility shim. Rejected because it would preserve the mismatch and hides the new contract.

- Keep `search_similar_by_id()` unchanged.
  - Rationale: the upstream change only affects text search; problem-id lookup remains on the existing endpoint.
  - Alternative considered: unify both paths behind one new client method. Rejected because it would add unnecessary indirection for a single compatibility fix.

- Preserve the bot-facing `search_similar_by_text()` return contract.
  - Rationale: downstream command code and UI helpers should not need to change.
  - Alternative considered: expose raw request/response handling in the cog. Rejected because it would leak transport details into command logic.

## Risks / Trade-offs

- [Deployment skew] Upstream API servers still on the old GET contract will reject POST requests → Coordinate deployment with the upstream API version or add an explicit fallback later if required.
- [Test drift] Existing tests may still assert GET query parameters → Update request-shape tests alongside the implementation.
- [Behavioral regression] The new body-based call could accidentally alter parameter mapping → Cover the exact payload shape in tests.
