# Changelog

All notable changes to this project will be documented in this file.

## [v1.1.0] - 2026-01-01
### Added
- `/similar` command for semantic similarity search of LeetCode problems using embeddings.
- Embedding CLI tool (`embedding_cli.py`) for building and querying problem embeddings.
- `EmbeddingRewriter`, `EmbeddingGenerator`, `EmbeddingStorage`, and `SimilaritySearcher` modules.
- Support for `.env` fallback mode with `DummyConfig` compatibility.

### Fixed
- Add empty rewrite validation with fallback in similar search.
- Add table whitelist validation to prevent SQL injection in storage.
- Add dimension type/range validation in `create_vec_table`.
- Fix `check_dimension_consistency` to return False on OperationalError.
- Remove redundant template assignment and duplicate imports.
- Change bare except to `except Exception` for proper exception handling.
- Fix variable shadowing in `similar_cog.py`.
- Add `cog_unload` to close database connection on unload.
- Add context manager protocol to `EmbeddingDatabaseManager`.
- Add embedding batch size mismatch check.
- Consolidate double retry logic in rewriter.

## [v1.0.2] - 2026-01-01
### Fixed
- Normalize LLM outputs to avoid inconsistent formatting.

### Documentation
- Add Docker run examples for both config.toml and .env setups.

### Maintenance
- Refresh the dependency lockfile for consistency.

## [v1.0.1] - 2026-01-01
### Fixed
- Use langchain-core prompt templates for improved LLM compatibility.

## [v1.0.0] - 2026-01-01
### Added
- Docker image publishing and documentation via GHCR workflow.

## Pre-1.0.0
### Added
- Automatic daily challenge posting with scheduled delivery per server.
- Slash commands for daily challenges, problem lookup, recent submissions, and server setup.
- Multi-server configuration with per-server channels, roles, and timezones.
- LeetCode.cn daily challenge support.
- LLM-powered translation and inspiration with caching.
- Historical daily challenges and monthly challenge fetching.
- Interactive embeds for problem details, submissions, and overview navigation.

### Improved
- Structured logging and APScheduler-based scheduling reliability.
- Data storage and caching for problem information and ratings.

### Fixed
- Scheduling, timezone handling, and interaction edge cases.
- Fix inspiration embed field names to display Chinese titles. (commit 5ec4446)
