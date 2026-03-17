## 1. Shared similar-results builder

- [x] 1.1 Add a single similar-result detail-button UI cap in `src/bot/utils/ui_constants.py` that represents the approved 25-button (5 rows × 5 buttons) limit
- [x] 1.2 Refactor `src/bot/utils/ui_helpers.py` so similar-result rendering goes through one shared builder that returns the embed plus an optional detail-button view
- [x] 1.3 Implement render-time gating in the shared builder so it attaches detail buttons only when the displayed result count is `<= 25` and every displayed result has button-safe `source` and `id` values
- [x] 1.4 Build similar-result detail buttons with problem-ID labels, preserved result ordering, `row=i // 5` layout, and `problem|{source}|{problem_id}|view` custom_ids

## 2. Slash `/similar` integration

- [x] 2.1 Update `src/bot/cogs/similar_cog.py` to use the shared similar-result builder instead of sending the embed directly
- [x] 2.2 Preserve the existing slash `/similar` input normalization so `top_k` remains clamped to `1..20` before calling the remote API
- [x] 2.3 Verify the slash flow sends embed + detail-button view for button-safe result sets and embed-only for overflow or invalid-result sets

## 3. Problem-card similar integration

- [x] 3.1 Update `src/bot/cogs/interaction_handler_cog.py` `_action_similar` to use the same shared similar-result builder as slash `/similar`
- [x] 3.2 Preserve the config-driven fetch behavior in the problem-card-triggered similar flow while applying the shared render-time safety gate only after results are returned
- [x] 3.3 Verify the problem-card-triggered similar flow degrades to embed-only when displayed results exceed 25 or any displayed result cannot safely reuse the existing `view` protocol

## 4. Protocol and regression tests

- [x] 4.1 Add or extend tests for the shared builder in the existing test suite so button-safe results produce one button per displayed result, with preserved order and bounded rows
- [x] 4.2 Add or extend slash-command tests to prove slash `/similar` keeps its `1..20` fetch clamp and reuses the shared similar-result rendering path
- [x] 4.3 Add or extend interaction-handler tests to prove similar-result detail buttons reuse `problem|{source}|{problem_id}|view` and still open the existing full problem card flow
- [x] 4.4 Add or extend tests for fail-closed behavior so overflow result sets and invalid routing fields always produce embed-only similar-result responses

## 5. Verification

- [x] 5.1 Run targeted tests covering `tests/test_interaction_handler.py` and the relevant slash/UI helper test files updated for this change
- [x] 5.2 Verify both `/similar` entry points now share the same detail-button rendering policy while keeping their approved fetch-count rules unchanged
- [x] 5.3 Run the full verification command set required for the change and confirm no local similarity index, local cache mapping, or alternate interaction protocol was introduced
