## Why

The project has been developed without formal specifications. As the codebase grows (cogs, LLM features, embedding search, multi-source support), there is no single source of truth for expected behavior, constraints, or contracts between modules. Initializing specs now captures existing behavior as a baseline, enabling spec-driven development for future changes.

## What Changes

- Document all existing capabilities as formal OpenSpec specifications
- No code changes — this is a documentation-only initialization
- Establish capability boundaries that map to the existing modular architecture

## Capabilities

### New Capabilities
- `bot-core`: Bot initialization, cog loading, shared resource lifecycle, Discord gateway events
- `daily-schedule`: APScheduler-based daily challenge scheduling, timezone-aware cron triggers, per-server job management
- `slash-commands`: Discord slash commands (`/daily`, `/problem`, `/set_channel`, `/set_role`, `/set_post_time`, `/set_timezone`, `/show_settings`, `/recent`, `/remove_channel`)
- `interaction-handler`: Persistent button interaction system for problem descriptions, LLM translations, LLM inspiration, submission navigation
- `leetcode-client`: LeetCode API client for .com and .cn domains, GraphQL queries, problem fetching, daily challenge retrieval, user submissions, retry logic
- `llm-integration`: Google Gemini LLM integration for translation and inspiration, structured output, caching
- `embedding-search`: Embedding pipeline (rewriter → generator → storage → searcher), CLI tooling, sqlite-vec vector search
- `database-layer`: SQLite database managers for settings, problems, daily challenges, embeddings, LLM caches; composite keys, cache TTL
- `configuration`: TOML-based config with environment variable overrides, model-specific settings, lazy singleton pattern
- `discord-ui`: Centralized embed/view/button creation, color/emoji mappings, Discord limit enforcement

### Modified Capabilities

(none — first-time initialization)

## Impact

- No code impact — specs document existing behavior only
- `openspec/specs/` will be populated with 10 capability spec files
- Future changes will reference these specs as the behavioral baseline
