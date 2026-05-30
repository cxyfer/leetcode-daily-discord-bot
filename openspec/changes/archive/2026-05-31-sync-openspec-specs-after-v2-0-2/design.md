## Context

The post-v2.0.2 codebase already contains the runtime behavior for i18n, locale-aware LLM caching, `/random` source filtering, tag autocomplete, and similar-search timeout handling. The OpenSpec state is partially synchronized: some archived change specs contain the missing contract, while several canonical `openspec/specs/*` files still describe the pre-i18n or incomplete behavior.

This change is specification-only. It consolidates the accepted runtime contract into OpenSpec delta specs so archive/apply workflows can update canonical specs without changing production code.

## Goals / Non-Goals

**Goals:**
- Add canonical capability coverage for i18n service behavior, locale-file contracts, and slash-command metadata localization.
- Update existing specs to reflect locale-aware configuration, persistence, Discord UI, interactions, scheduled posts, and LLM behavior.
- Clarify public `/random` source filtering and tag autocomplete edge cases.
- Clarify similar-search timeout and inflight deduplication semantics.
- Keep each delta spec focused on observable requirements and testable scenarios.

**Non-Goals:**
- Do not modify runtime Python code, SQL schema files, tests, dependencies, or deployment configuration.
- Do not introduce new behavior beyond what the post-v2.0.2 implementation and archived OpenSpec artifacts already imply.
- Do not archive the change in this step.

## Decisions

### Decision: Treat this as a specification synchronization change

Use OpenSpec delta files only. Runtime code changes are out of scope because the audit found missing or stale canonical contracts rather than a required implementation feature.

Alternative considered: open separate behavior fixes for each gap. That would unnecessarily expand the scope and risk changing already-working code while the immediate problem is canonical spec drift.

### Decision: Promote i18n artifacts into three new capabilities

Create `i18n-service`, `locale-files`, and `command-localization` as standalone capabilities. These concepts cut across slash commands, UI, interactions, scheduling, and LLM features, so keeping them separate prevents repeated low-level locale requirements in every existing spec.

Alternative considered: fold all i18n requirements into `configuration` and `slash-commands`. That would make those specs too broad and obscure service-level behavior such as fallback, interpolation, and locale-file validation.

### Decision: Use modified existing capabilities for user-visible behavior changes

Update `configuration`, `database-layer`, `slash-commands`, `discord-ui`, `interaction-handler`, `daily-schedule`, `llm-integration`, `tag-autocomplete`, and `embedding-search` via delta specs. These are existing OpenSpec capabilities whose observable requirements changed or need clarification.

Alternative considered: create a single `openspec-sync` capability. That would not archive cleanly into the canonical capability model and would make future verification harder.

### Decision: Specify intended similar-search dedup semantics explicitly

The canonical spec will state how per-request timeout interacts with inflight request keys. This removes ambiguity between archived design notes and current implementation expectations.

Alternative considered: leave the ambiguity unresolved. That would preserve a known source of drift and make future API-client reviews inconclusive.

## Risks / Trade-offs

- Spec drift from implementation details → Mitigation: write observable requirements and scenarios, not line-by-line implementation descriptions.
- Large delta surface area → Mitigation: split by capability and keep each spec focused on the smallest contract needed.
- Archive conflicts with existing canonical specs → Mitigation: use existing capability names for modified specs and exact requirement names where modifying an existing requirement.
- Similar dedup semantics may still need product confirmation → Mitigation: document the intended contract clearly so any future implementation mismatch can be handled as a separate fix.

## Migration Plan

1. Create delta specs for all capabilities listed in the proposal.
2. Create a task list for applying and verifying the spec-only sync.
3. Run OpenSpec validation/status checks.
4. Apply/archive through the normal OpenSpec workflow when ready.

Rollback is straightforward: revert this OpenSpec change directory before archiving, or archive a follow-up delta if the intended contract changes later.

## Open Questions

- Should similar-search inflight dedup ignore timeout to maximize coalescing, or include timeout to keep different caller contracts isolated? This change records the current intended contract; any disagreement should become a focused follow-up change.
