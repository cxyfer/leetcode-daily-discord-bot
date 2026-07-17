## 1. Additional daily API and payload contract

- [x] 1.1 Add API-client tests for `source`-only daily requests, optional dates, full envelope preservation, and unchanged v0.4 LeetCode normalization.
- [x] 1.2 Add `OjApiClient.get_daily_by_source()` while retaining the existing `get_daily(domain, date)` public contract.
- [x] 1.3 Add payload tests for complete ordered problem preservation, target/date in-flight reuse, target cache isolation, and no LeetCode history fan-out for additional sources.
- [x] 1.4 Extend `get_daily_payload()` with an explicit additional-source target, namespaced cache keys, a complete `problems` list, and backward-compatible LeetCode payload fields.

## 2. Safe reusable multi-problem presentation

- [x] 2.1 Add UI-helper tests for ordered overview buttons, exact 25-button layout, unsafe routing fields, over-limit payloads, and localized daily footer overrides.
- [x] 2.2 Generalize the existing problem-detail button safety decision and make `create_problems_overview_view()` return no view unless every displayed problem is safely representable.
- [x] 2.3 Extend the overview embed builder only as needed to accept localized daily-specific footer text without changing existing `/problem` output.

## 3. Manual `/daily_extra` command

- [x] 3.1 Add slash-command tests for exact source choices, current/date requests, default-private and explicit-public initial responses, single-problem cards, ordered multi-problem overviews, invalid dates, missing data, unsafe payloads, and API error mapping.
- [x] 3.2 Implement `/daily_extra source:<sheep|0x3f> [date] [public]` by composing the source-aware payload and existing problem/overview builders.
- [x] 3.3 Add `sheep` and `0x3f` display labels plus zh-TW, en-US, and zh-CN metadata, footer, not-found, and payload-limit translations with locale key parity.
- [x] 3.4 Add an interaction regression test proving an overview `view` click remains ephemeral and does not edit the original overview; do not add a new interaction route.

## 4. Documentation and compatibility

- [x] 4.1 Document `/daily_extra`, its sources, date/public parameters, multi-problem overview, and private selected details in `README.md`.
- [x] 4.2 Verify `/daily`, `/daily_cn`, scheduled daily delivery, and oj-api-rs v0.4 LeetCode compatibility remain unchanged.

## 5. Validation

- [x] 5.1 Run focused API, payload, UI, slash-command, interaction, i18n, and history-date tests.
- [x] 5.2 Run `openspec validate add-daily-extra-command --strict --no-interactive`.
- [x] 5.3 Run `uv run --extra dev ruff check .` and `uv run --extra dev pytest` with writable runtime log/cache paths.
  - Ruff passes. The full suite has 229 passing tests and 3 pre-existing worktree-only path assertions caused by the intentionally symlinked `config.toml` and `data/data.db` resolving to the main checkout.
