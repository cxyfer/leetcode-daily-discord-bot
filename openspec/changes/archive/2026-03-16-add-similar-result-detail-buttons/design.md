## Context

`/similar` currently renders results as an embed only in both entry points: the slash command path in `src/bot/cogs/similar_cog.py` and the problem-card-triggered path in `src/bot/cogs/interaction_handler_cog.py`. The repository already has a persistent interaction protocol for full problem cards, `problem|{source}|{problem_id}|view`, and the interaction handler already routes that protocol to `_action_view()`.

The requested change is intentionally presentation-scoped. It must add direct detail entry points to similar-result responses without changing the remote API-only ownership of similarity search. The change also has to respect Discord component limits and keep both `/similar` entry points behaviorally aligned, even though their fetch-count rules are not identical today: slash `/similar` clamps user input to 20, while the problem-card-triggered similar flow uses config-driven `top_k`.

The current codebase already uses a 5 rows × 5 buttons layout for problem overview detail buttons. This existing constraint is the approved UI ceiling for similar-result detail buttons as well.

## Goals / Non-Goals

**Goals:**
- Add direct detail buttons to similar-result responses when the response is safe to render within Discord button limits.
- Reuse the existing `problem|{source}|{problem_id}|view` interaction protocol and existing full-card handling flow.
- Keep slash `/similar` and problem-card-triggered similar responses on one shared rendering path so the same payload produces the same embed/view outcome.
- Preserve the current remote API-only architecture for similarity lookup and problem-detail loading.
- Define explicit fail-closed rules for overflow and invalid result data so implementation has no runtime policy ambiguity.

**Non-Goals:**
- No new interaction protocol, no new button router, and no session/stateful mapping layer for similar results.
- No change to similarity backend ownership, no local embedding index, and no eager problem-detail prefetch for each result.
- No change to slash `/similar` fetch clamping behavior beyond the existing `1..20` input normalization.
- No requirement to make problem-card-triggered similar fetch counts match slash `/similar`; only the rendering policy must be shared.
- No partial-button fallback when rendering is unsafe. Unsafe responses remain embed-only.

## Decisions

### 1. Use one shared similar-results message builder
**Decision:** Similar-result rendering will be centralized in a shared UI helper under `src/bot/utils/ui_helpers.py`. Both the slash `/similar` flow and the problem-card-triggered similar flow must call the same builder to produce the embed and the optional detail-button view.

**Rationale:** The two entry points currently construct the same embed in different cogs. Duplicating the new button logic in both places would create drift in limit handling, invalid-result handling, and button ordering.

**Alternatives considered:**
- Add button logic separately in each cog: rejected because it would duplicate policy and increase the risk of inconsistent behavior.
- Create a stateful mapping from result index to problem id: rejected because the existing `problem|...|view` protocol already carries the required routing data.

### 2. Treat 25 buttons as the only approved similar-detail UI cap
**Decision:** The similar-result detail-button ceiling is 25 buttons, aligned with the existing 5 rows × 5 buttons layout already used elsewhere in the project.

**Rationale:** The repository already encodes this Discord-safe layout for overview buttons. Reusing the same ceiling avoids introducing a second UI limit system.

**Alternatives considered:**
- Keep a separate 20-button render cap: rejected because 20 is the slash fetch clamp, not the approved Discord component ceiling.
- Make the cap configurable: rejected because Discord component safety is a platform invariant, not an environment-specific product setting.

### 3. Preserve existing fetch behavior, apply safety only at render time
**Decision:** Slash `/similar` keeps its current input clamp to `1..20`. The problem-card-triggered similar flow continues to fetch using `config.similar.top_k`. The shared builder decides only whether buttons can be attached to the returned result set.

**Rationale:** This keeps the change scoped to presentation and avoids silently changing existing fetch semantics for the config-driven path.

**Alternatives considered:**
- Clamp the problem-card-triggered path to 20 as well: rejected because the approved decision was to preserve current config-driven fetch behavior.
- Clamp both paths to 25: rejected because it would change existing slash command behavior without a product requirement.

### 4. Use all-or-nothing button rendering
**Decision:** A similar-result response gets detail buttons only when all displayed results are button-safe and the displayed result count is `<= 25`. Otherwise, the response must degrade to embed-only.

A result is button-safe only if it can be losslessly mapped to the existing protocol `problem|{source}|{problem_id}|view`, which requires valid `source` and `id` values that do not corrupt routing.

**Rationale:** Partial button rendering would create a confusing UI where some listed results can open details and others cannot. The approved behavior is fail-closed, not best-effort.

**Alternatives considered:**
- Show buttons for the first 25 results only: rejected because it breaks parity between the embed list and interactive affordances.
- Skip only invalid items and show buttons for the rest: rejected because it breaks the one-result/one-detail-entry mental model.

### 5. Keep button presentation stable and protocol-compatible
**Decision:** Each detail button label uses the problem ID, and buttons preserve the same order as the embed result list. Buttons reuse the existing custom id format `problem|{source}|{problem_id}|view` and are laid out with at most 5 buttons per row.

**Rationale:** Problem ID labels align with the existing overview-detail buttons, remain compact enough for Discord UI, and avoid introducing a second labeling convention.

**Alternatives considered:**
- Label buttons by rank (`1`, `2`, `3`): rejected because it is less informative than the problem ID and adds another translation layer for users.
- Label buttons by title: rejected because titles are too wide and unstable for compact button layouts.

### 6. Keep the detail flow stateless and reuse existing full-card behavior
**Decision:** Clicking a similar-result detail button continues through the existing `_action_view()` path, which fetches the full problem detail lazily and returns the full problem card via the existing interaction handler.

**Rationale:** The routing logic already exists and already supports cross-source problem detail buttons. Reusing it keeps the change mechanical and preserves remote-only ownership.

**Alternatives considered:**
- Add a special similar-detail action: rejected because it would duplicate behavior already provided by `view`.
- Preload full problem details while building similar results: rejected because it adds avoidable remote calls and changes the architecture from lazy detail loading to eager enrichment.

### 7. Verify the change through shared-builder and protocol tests
**Decision:** Tests for this change must cover the shared builder, cross-entrypoint parity, all-or-nothing fallback, 25-button row packing, and reuse of the existing `problem|...|view` protocol.

**Rationale:** The main risk is policy drift or accidental protocol breakage, not algorithmic complexity. Verification must therefore focus on invariants and edge cases rather than only happy-path snapshots.

**Alternatives considered:**
- Test only one entry point: rejected because the feature requirement explicitly covers both `/similar` paths.
- Test only UI snapshots: rejected because routing and fallback behavior are equally important.

## Risks / Trade-offs

- **Config-driven similar may fetch more than 25 results and therefore often render embed-only** → Mitigation: document that the render rule depends on returned result count, not requested count, and keep this behavior explicit in specs and tests.
- **Remote API result items may occasionally miss button-safe `source` or `id` values** → Mitigation: fail closed to embed-only and test invalid-result behavior directly.
- **Large but still valid button sets can feel dense on mobile Discord clients** → Mitigation: preserve compact problem-ID labels and stable ordering; do not widen labels to titles.
- **Shared-builder refactor touches two entry points at once** → Mitigation: keep the builder narrowly scoped to similar-result rendering and verify parity with focused tests.
- **The project already has both a slash fetch clamp and a UI button cap** → Mitigation: state clearly that fetch normalization and render safety are distinct rules with different purposes.

## Migration Plan

1. Add or formalize a single similar-result detail-button UI cap in the shared UI constants layer.
2. Introduce a shared similar-results message builder that produces the embed plus an optional detail-button view.
3. Encode render-time gating in the shared builder: only attach a view when displayed results are all button-safe and the displayed result count is `<= 25`.
4. Update the slash `/similar` flow to use the shared builder without changing its existing fetch clamp behavior.
5. Update the problem-card-triggered similar flow to use the same shared builder without changing its config-driven fetch behavior.
6. Add tests covering cross-entrypoint parity, protocol reuse, all-or-nothing fallback, and 25-button row packing.
7. Verify that unsafe responses remain embed-only and that detail-button clicks still route through the existing `_action_view()` full-card flow.

**Rollback strategy:** Revert the shared-builder integration and restore embed-only similar-result responses in both entry points. Because the change is presentation-scoped and stateless, rollback is a clean revert of UI helper and cog wiring changes.

## Open Questions

None. The remaining policy decisions for this change have been explicitly resolved, so implementation can proceed mechanically from the approved constraints.
