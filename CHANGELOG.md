# Changelog

All notable changes to this project will be documented in this file.

## [v1.1.4] - 2026-01-07
### Changed
- **Unified GenAI Client**: Replaced `langchain` and `langchain-google-genai` with direct `google-genai` SDK integration for simpler and more efficient LLM operations. (#20)
- **Native JSON Parsing**: Replaced `langchain_core.output_parsers.SimpleJsonOutputParser` with native Python JSON parsing.
- **Plain String Templates**: Replaced `langchain_core.prompts.PromptTemplate` with plain Python string templates.

### Added
- **Third-Party Proxy Support**: Added `base_url` configuration option under `[llm.gemini]` to support third-party API proxies.
- **Per-Model Credentials**: Added optional `api_key` and `base_url` configuration for embedding and rewrite models with inheritance logic (model-specific → global → environment variables).
- **SDK Retry Options**: Implemented retry logic using SDK's native `HttpRetryOptions` for better reliability.
- **Debug Logging**: Added DEBUG-level logging for EmbeddingGenerator and EmbeddingRewriter configuration inspection.

### Fixed
- **Timeout Unit**: Clarified that `HttpOptions.timeout` expects milliseconds (SDK requirement).
- **Base URL Format**: Corrected base_url example to use `https://generativelanguage.googleapis.com` without `/v1beta` suffix.

### Removed
- **Langchain Dependencies**: Removed `langchain` and `langchain-google-genai` from project dependencies, reducing package size and complexity.

## [v1.1.3] - 2026-01-06
### Added
- **Codeforces Platform Support**: Complete integration of Codeforces as a problem source with problemset sync, contest list, standings parsing, and problem content fetching. (#18)
- **Codeforces in `/problem` Command**: Integrated Codeforces problems into the `/problem` command with tags and rating display. (#18)
- **Cloudflare Bypass**: Use `curl_cffi` to bypass Cloudflare protection for Codeforces requests. (#18)
- **Content Reprocessing CLI**: Added `--reprocess-content` CLI flag for AtCoder and Codeforces clients to batch reprocess stored content. (#19)
- **Batch Update API**: Added `batch_update_content()` method with tuple return for error detection and incremental flush. (#19)
- **Shared HTML Utilities**: Extracted `normalize_math_delimiters()` to shared `html_converter` module. (#19)

### Improved
- **HTML-to-Markdown Pipeline**: Implemented comprehensive HTML-to-Markdown conversion for Codeforces and AtCoder problem content. (#19)
- **Memory Efficiency**: Optimized `reprocess_content()` with incremental batch flush to reduce memory peak. (#19)
- **Progress Logging**: Added progress logging every 50 items during content reprocessing. (#19)
- **Embed UI**: Enhanced embed UI to show Source field as standalone row. (#18)

### Fixed
- **LaTeX Delimiters**: Normalized triple dollar (`$$$`) LaTeX delimiters to single dollar (`$`). (#19)
- **Relative URLs**: Fixed relative URL conversion to absolute URLs in problem content. (#19)

## [v1.1.2] - 2026-01-05
### Added
- **Development Dependencies**: Added `ruff` and `pytest` as optional development dependencies.
- **Ruff Configuration**: Configured `ruff` for linting and formatting with a 120-character line length limit.
- **Pytest Configuration**: Configured `pytest` with `asyncio` support and coverage reporting.
- **GitHub Actions CI**: Added a new CI workflow to automatically run `ruff` and `pytest` on push and pull requests.
- **Developer Documentation**: Added a "Development" section to `README.md` with instructions for environment setup and tool usage.

### Improved
- **Code Quality**: Applied comprehensive `ruff` formatting and fixed all linting issues across the codebase.
- **Import Organization**: Standardized import sorting across all Python files.

## [v1.1.1] - 2026-01-04
### Added
- **AtCoder Platform Support**: Complete integration of AtCoder as a problem source, including fetching, translation, and semantic search.
- **Multi-Source Database Schema**: Migration to a flexible schema supporting multiple competitive programming platforms.
- **AI Rewritten Query Display**: The `/similar` command now displays both the original query and the AI-rewritten keywords for better transparency.
- **Expanded Source Support**: Enhanced source detection logic to support LeetCode Contest, Codeforces, and Luogu URLs and problem ID formats.
- **Multi-Platform URL Detection**: Added support for Luogu transcribed problems (including UVA, SPOJ) and improved parsing for Codeforces Contest/Problemset URLs.

### Improved
- **AtCoder UI & Parsing**: Optimized HTML-to-Markdown conversion for AtCoder problems, including better MathJax and table support.
- **LLM Structured Output**: Migrated LLM translations and inspirations to use Gemini's native structured outputs and Pydantic models for higher reliability.
- **Dynamic Result Batching**: Implemented character-length-aware batching for search results to strictly adhere to Discord's 1024-character field limit.
- **Increased Search Limit**: Raised the maximum `top_k` results for `/similar` from 10 to 20.
- **Standardized UI**: Improved formatting consistency using global UI constants and refined emojis (❓, 🤖, 🔍).

### Fixed
- Fixed AtCoder-specific issues including 403 Forbidden errors, header normalization, and UI edge cases.
- Fixed an issue where certain LeetCode URLs were not correctly identified as problem IDs.
- Fixed validation logic for source prefixes and recursive handling for nested prefixes.

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
