## Context

The bot's LeetCode `/daily` and `/daily_cn` flows already consume the normalized oj-api-rs daily envelope, but `get_daily_payload()` collapses that envelope to `problems[0]` and performs LeetCode-specific historical lookups. The current oj-api-rs `dev` contract also accepts `source=sheep` and `source=0x3f`; those records can contain multiple ordered problems and can return `202` while ingestion is running or `404` for unavailable source/date combinations.

The bot already has the interaction primitives needed for a multi-problem response: `create_problems_overview_embed()`, `create_problems_overview_view()`, and the persistent `problem|{source}|{problem_id}|view` route. The `view` handler fetches the selected problem and sends its full card ephemerally. Reusing these owners avoids shared mutable page state and prevents one user's click from replacing another user's view.

The first delivery is intentionally manual-only. Existing LeetCode commands, configured scheduled posts, database state, and guild configuration remain outside this change.

## Goals / Non-Goals

**Goals:**

- Add `/daily_extra source:<sheep|0x3f> [date] [public]` with localized metadata and responses.
- Preserve every problem and its upstream order from the daily envelope.
- Render one problem directly and multiple problems as a safe overview.
- Keep selected problem details private to the clicking user.
- Keep cache/in-flight reuse collision-free across LeetCode domains and additional sources.
- Preserve all existing LeetCode daily behavior and oj-api-rs v0.4 LeetCode normalization.

**Non-Goals:**

- Add `sheep` or `0x3f` to scheduled delivery.
- Add guild configuration, database schema, or persistence for additional sources.
- Add message-editing pagination, per-user view state, or a daily-specific custom-id protocol.
- Add client-side source availability calendars; oj-api-rs remains authoritative for first-date and weekday availability.
- Add more daily sources beyond `sheep` and `0x3f`.

## Decisions

### Keep the additional-source API call separate from the legacy-compatible LeetCode method

Add `OjApiClient.get_daily_by_source(source, date=None)` and share only the internal request/envelope handling needed by both daily methods. Keep `get_daily(domain="com", date=None)` and `_normalize_daily_response()` behavior stable so configured oj-api-rs v0.4 backends continue to support `/daily` and `/daily_cn`.

The additional-source method sends `source` and optional `date` parameters without a `domain` parameter. It does not claim v0.4 support because those sources are available only on the newer upstream contract.

Alternative considered: add a `source` keyword to `get_daily()`. Its default `domain="com"` makes conflict-free parameter construction easy to misuse, and changing the signature weakens the existing compatibility boundary.

### Generalize the existing payload cache around an explicit request target

Extend `get_daily_payload()` with an optional additional-source target while preserving current positional LeetCode callers. Build cache and in-flight keys from an explicit namespace (`domain:com`, `domain:cn`, `source:sheep`, or `source:0x3f`) plus explicit/resolved date. Return the complete `problems` list in the payload while retaining `challenge_info` as the first problem for existing callers.

Only LeetCode domain targets perform historical same-day fan-out. Additional-source targets return an empty `history_problems` list because the existing history presentation and date semantics are LeetCode-specific.

Alternative considered: create a separate uncached `get_extra_daily_payload()` path. That duplicates cache, in-flight, date-resolution, and envelope-validation ownership and creates inconsistent request behavior.

### Reuse the existing overview and unified detail interaction

For one problem, `/daily_extra` uses the existing full problem embed/view builders with an additional-source daily footer. For multiple problems, it uses the existing overview embed/view builders, preserving upstream order and using each problem's own `source` and `id` in `problem|{source}|{problem_id}|view`.

The overview builder receives localized daily-specific title/footer text. The generic problem-overview view gains an all-or-nothing safety decision shared with existing detail-button validation: every displayed item must have safe routing segments, every custom id must fit Discord limits, and the complete result set must fit within 25 buttons. An unsafe payload produces a localized command error and no partial overview.

Alternative considered: add two daily-specific toggle buttons or edit the original message in place. That would introduce shared state and allow concurrent users to overwrite the same message.

Alternative considered: add a daily-specific custom-id and interaction handler. The existing stateless problem action protocol already carries all required routing data.

### Separate initial response visibility from detail visibility

`public=false` remains the default and makes the initial direct card or overview ephemeral. `public=true` makes only that initial response public. Every overview `view` click continues to defer and respond ephemerally through the existing interaction handler, and the original overview is never edited.

### Keep upstream availability and processing authoritative

The command validates only the local `YYYY-MM-DD` shape before requesting data. A `404`/empty result becomes a localized source/date not-found response, `202` continues through `ApiProcessingError`, and network/rate-limit/generic failures reuse the existing localized API error flow. The bot does not copy Sheep/0x3f weekday or first-date rules.

## Risks / Trade-offs

- **An additional-source response contains more than 25 problems or an unsafe ID** → Reject the payload with a localized error instead of silently omitting buttons or creating an unrouteable interaction.
- **The generic daily payload helper becomes harder to reason about** → Keep the target choice explicit, preserve existing positional domain calls, namespace cache keys, and cover domain/source isolation with focused tests.
- **Additional-source titles or links are sparse** → Continue using the existing source-aware problem card and overview rendering; missing required routing/display fields fail closed rather than producing partial UI.
- **A public overview exposes the list to everyone** → This is explicitly controlled by `public`; selected details remain ephemeral and stateless.
- **A v0.4 backend rejects `source`** → `/daily_extra` reports the normal localized API failure while existing LeetCode commands retain v0.4 compatibility.

## Migration Plan

1. Deploy the command, locale keys, client method, payload changes, and tests together.
2. Let the normal Discord command sync register `/daily_extra`; no data migration or configuration update is required.
3. Roll back by reverting this change. Existing `/daily`, `/daily_cn`, scheduler, and database state remain compatible because their public contracts are unchanged.

## Open Questions

None. The approved first-stage scope is manual lookup only, with overview-first multi-problem display and ephemeral selected details.
