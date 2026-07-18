# Proof Bundle - 2026-07-18-redesign-daily-push-mechanism

## Method Pack Boundary

This proof bundle is an advisory Aegis Method Pack record. It does not determine evidence sufficiency, produce authoritative `GateDecision`, or grant `completion authority`.

## Task Intent

- Requested outcome: Allow each Discord server to configure one independent scheduled push for each of leetcode.com, sheep, and 0x3f
- Scope: Database schema and migration, config command behavior, APScheduler job ownership, daily API source selection, multi-problem scheduled rendering, localization, tests, and docs

## Impact

- Compatibility boundary: Existing /config invocations without source continue to manage leetcode.com and legacy settings migrate without data loss
- Non-goals:
- Multiple pushes for the same source
- Persistent cross-process delivery history
- Changes to upstream source availability rules

## Evidence Bundle Refs

- docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/evidence-bundle-draft-aegis-workspace-check.json
- docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/evidence-bundle-draft-final-full-verification-green.json
- docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/evidence-bundle-draft-openspec-strict-validation.json
- docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/evidence-bundle-draft-task1-schema-assets-green.json
- docs/aegis/work/2026-07-18-redesign-daily-push-mechanism/evidence-bundle-draft-task2-database-green.json

## Drift Check

- Scope status: Implementation remains within the approved three-source schema, scheduler, config, rendering, localization, tests, and documentation scope.
- Compatibility status: Source-less config still targets leetcode.com; manual domain calls and legacy reset IDs remain supported; legacy rows are backed up and migrated without dual reads.
- Retirement status: Combined CRUD, live legacy delivery columns, server-only job IDs, and hard-coded com delivery keys are retired; legacy reads are isolated to the one-way migration owner.
- Advisory decision: continue
