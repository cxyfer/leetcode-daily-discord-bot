# Implement /daily_extra command - Intent

## TaskIntentDraft

- Requested outcome: Implement the approved manual /daily_extra command for sheep and 0x3f with ordered multi-problem overview and private selected details
- Goal: Complete all four implementation-plan slices and prove the OpenSpec acceptance boundary
- Success evidence:
- Focused and full pytest pass; Ruff, OpenSpec strict validation, Aegis workspace check, and diff check pass
- Stop condition: done when every plan/OpenSpec task is implemented and verified; otherwise report blocked, needs-verification, or scope-exceeded
- Non-goals:
- No scheduler support for extra sources
- No database or configuration changes
- No pagination, message editing, or new interaction protocol
- Scope: API client, daily payload cache, overview UI safety, slash command, i18n, privacy regression tests, README, and verification
- Change kinds:
- feature
- Risk hints:
- Cross-module API/cache/UI contract; preserve v0.4 LeetCode and scheduled delivery behavior

## BaselineReadSetHint

- openspec/changes/add-daily-extra-command
- docs/aegis/plans/2026-07-16-add-daily-extra-command.md
- /home/usaya/workspace/github/oj-api-rs/openspec/specs/daily-challenge/spec.md@4536487

## BaselineUsageDraft

- Required baseline refs:
- openspec/changes/add-daily-extra-command
- docs/aegis/plans/2026-07-16-add-daily-extra-command.md
- /home/usaya/workspace/github/oj-api-rs/openspec/specs/daily-challenge/spec.md@4536487
- Acknowledged before plan:
- none
- Cited in plan:
- none
- Missing refs:
- openspec/changes/add-daily-extra-command
- docs/aegis/plans/2026-07-16-add-daily-extra-command.md
- /home/usaya/workspace/github/oj-api-rs/openspec/specs/daily-challenge/spec.md@4536487
- Advisory decision: needs-baseline-readback

## ImpactStatementDraft

- Compatibility boundary: Keep get_daily(domain,date), v0.4 normalization, /daily, /daily_cn, scheduling, DB, config, and problem custom ids stable
- Affected layers:
- API client
- daily payload cache
- Discord command/UI
- Owners:
- Existing OjApiClient, get_daily_payload, ui_helpers, SlashCommandsCog, and InteractionHandlerCog owners
- Invariants:
- Cache identity is request-target namespace plus date; selected details are always ephemeral
- Non-goals:
- No scheduler support for extra sources
- No database or configuration changes
- No pagination, message editing, or new interaction protocol

These records are Method Pack drafts / hints, not authoritative runtime decisions.

## BaselineUsageDraft

- Required baseline refs:
- openspec/changes/add-daily-extra-command
- openspec/specs/interaction-handler/spec.md
- openspec/specs/discord-ui/spec.md
- Delivered context refs:
- existing api_client ui_helpers slash_commands interaction_handler and locale owners
- Acknowledged before plan:
- docs/aegis/plans/2026-07-16-add-daily-extra-command.md
- Cited in plan:
- upstream oj-api-rs dev daily source contract
- Missing refs:
- none
- Advisory decision: continue
