## Context

This is a first-time specification initialization for an existing Discord bot project. The codebase is stable and in production. No architectural changes are being made — this design documents the existing architecture to establish a baseline for future spec-driven development.

The bot uses discord.py's Cog-based modular architecture with shared resources attached to the bot instance. Data persistence uses SQLite with multiple specialized database managers. External integrations include LeetCode GraphQL API, Google Gemini LLM, and sqlite-vec for vector search.

## Goals / Non-Goals

**Goals:**
- Capture all existing capabilities as formal specifications
- Establish behavioral contracts between modules
- Create a verifiable baseline for regression detection

**Non-Goals:**
- Refactoring or changing any existing code
- Adding new features or capabilities
- Defining future roadmap items
- Performance optimization

## Decisions

1. **10 capability boundaries aligned with module structure**: Each spec maps to a natural code boundary (cog, utility module, or integration layer). This avoids artificial splits and keeps specs maintainable.

2. **All requirements use ADDED (not MODIFIED)**: Since no prior specs exist, every requirement is new from OPSX's perspective, even though the code already implements them.

3. **Scenarios derived from existing behavior**: Each scenario documents what the code currently does, not aspirational behavior. This ensures specs are immediately verifiable against the running system.

## Risks / Trade-offs

- **Spec drift**: Specs may diverge from code if future changes bypass the spec workflow. → Mitigation: Enforce spec-driven changes via OPSX workflow.
- **Over-specification**: Documenting implementation details as requirements reduces flexibility. → Mitigation: Specs focus on observable behavior, not internal implementation.
- **Incomplete coverage**: Some edge cases may be missed in initial documentation. → Mitigation: Specs can be incrementally refined through future changes.
