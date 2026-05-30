## 1. Spec Synchronization

- [x] 1.1 Apply the new `i18n-service` canonical spec from the change delta.
- [x] 1.2 Apply the new `locale-files` canonical spec from the change delta.
- [x] 1.3 Apply the new `command-localization` canonical spec from the change delta.
- [x] 1.4 Apply locale-aware updates to `configuration`, `database-layer`, `slash-commands`, `discord-ui`, `interaction-handler`, `daily-schedule`, and `llm-integration` canonical specs.
- [x] 1.5 Apply `/random` source, `source=all`, tag autocomplete, and similar-search timeout/dedup clarification updates.

## 2. Validation

- [x] 2.1 Run OpenSpec status/validation for `sync-openspec-specs-after-v2-0-2`.
- [x] 2.2 Review generated canonical spec deltas for requirement headings, `#### Scenario` formatting, and archive compatibility.
- [x] 2.3 Confirm the change is specification-only and does not modify runtime Python, SQL, dependency, or deployment files.

## 3. Finalization

- [x] 3.1 Resolve or explicitly accept the similar-search inflight timeout/dedup open question.
- [ ] 3.2 Archive the completed change through the normal OpenSpec archive workflow when validation passes.
