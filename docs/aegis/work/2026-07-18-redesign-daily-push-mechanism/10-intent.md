# Redesign daily push mechanism - Intent

## TaskIntentDraft

- Requested outcome: Allow each Discord server to configure one independent scheduled push for each of leetcode.com, sheep, and 0x3f
- Goal: Allow each Discord server to configure one independent scheduled push for each of leetcode.com, sheep, and 0x3f
- Success evidence:
- Schema migration preserves legacy LeetCode pushes; each source schedules and delivers independently; targeted and full tests pass
- Stop condition: Done when approved OpenSpec requirements are implemented and verified; otherwise stop as blocked, needs-verification, or scope-exceeded
- Non-goals:
- Multiple pushes for the same source
- Persistent cross-process delivery history
- Changes to upstream source availability rules
- Scope: Database schema and migration, config command behavior, APScheduler job ownership, daily API source selection, multi-problem scheduled rendering, localization, tests, and docs
- Change kinds:
- architecture-contract-migration
- Risk hints:
- Persistent SQLite migration and compatibility of existing /config behavior

## BaselineReadSetHint

- openspec/specs/database-layer/spec.md
- openspec/specs/daily-schedule/spec.md
- openspec/specs/slash-commands/spec.md
- openspec/specs/leetcode-client/spec.md

## BaselineUsageDraft

- Required baseline refs:
- openspec/specs/database-layer/spec.md
- openspec/specs/daily-schedule/spec.md
- openspec/specs/slash-commands/spec.md
- openspec/specs/leetcode-client/spec.md
- Acknowledged before plan:
- none
- Cited in plan:
- none
- Missing refs:
- openspec/specs/database-layer/spec.md
- openspec/specs/daily-schedule/spec.md
- openspec/specs/slash-commands/spec.md
- openspec/specs/leetcode-client/spec.md
- Advisory decision: needs-baseline-readback

## ImpactStatementDraft

- Compatibility boundary: Existing /config invocations without source continue to manage leetcode.com and legacy settings migrate without data loss
- Affected layers:
- persistence
- Discord command surface
- scheduler
- API client and UI rendering
- Owners:
- SettingsDatabaseManager; SlashCommandsCog; ScheduleManagerCog; OjApiClient; ui_helpers
- Invariants:
- At most one push per server and supported source, with at most three pushes per server
- Non-goals:
- Multiple pushes for the same source
- Persistent cross-process delivery history
- Changes to upstream source availability rules

These records are Method Pack drafts / hints, not authoritative runtime decisions.
