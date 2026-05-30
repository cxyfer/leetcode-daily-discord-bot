# embedding-search Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Similarity search uses the remote API backend
The `/similar` command SHALL use the remote API exposed through the application API client as its only similarity-search backend. The runtime SHALL resolve similar problems by calling the API client from the packaged runtime namespace and SHALL NOT depend on local embedding indices, local vector stores, or local embedding generation workflows. The similar API calls SHALL use a per-request timeout from `SimilarConfig.timeout` to accommodate potentially long embedding computation times, and SHALL distinguish `ApiEmbeddingError` (502), `ApiEmbeddingTimeoutError` (504), and `ApiError` (other statuses) for error reporting.

#### Scenario: Search by problem
- **WHEN** a user runs `/similar` with a problem parameter
- **THEN** the system SHALL resolve the problem identifier as needed and call the API client's remote similar-by-id endpoint with the configured similar timeout to fetch results

#### Scenario: Search by text query
- **WHEN** a user runs `/similar` with a text query
- **THEN** the system SHALL call the API client's remote text-search endpoint with the configured similar timeout to fetch similar problems using a POST JSON request body

#### Scenario: Shared result presentation
- **WHEN** similar problems are found from either `/similar` entry point
- **THEN** the system SHALL render the remote API response through the shared similarity-result builder used by the feature

#### Scenario: Conditional detail-button presentation
- **WHEN** the remote API returns a button-safe result set
- **THEN** the system SHALL attach direct detail buttons that reuse the existing `problem|{source}|{problem_id}|view` protocol without performing eager per-result problem-detail fetches

#### Scenario: Unsafe result presentation remains remote-only
- **WHEN** the remote API returns a result set that exceeds the safe detail-button limit or contains a displayed item with invalid routing fields
- **THEN** the system SHALL degrade to embed-only without introducing any local similarity cache, local index lookup, or alternate data source

#### Scenario: Runtime ownership
- **WHEN** runtime code performs similarity search after the source layout is reorganized under `src/bot/`
- **THEN** ownership SHALL remain within packaged runtime modules such as `bot.api_client` and `bot.cogs.similar_cog`

#### Scenario: Button-triggered similar uses same timeout and error contract
- **WHEN** a problem-card similar button triggers a similarity search
- **THEN** the system SHALL call the API client with the same configured timeout as the slash command and SHALL handle `ApiEmbeddingError`, `ApiEmbeddingTimeoutError`, and `ApiError` with differentiated localized messages

### Requirement: No local similarity maintenance workflow
The repository SHALL NOT document or require local embedding build, rebuild, query, or vector-storage workflows for `/similar`.

#### Scenario: Documentation guidance
- **WHEN** runtime or developer documentation describes `/similar`
- **THEN** it SHALL describe the feature as remote-only and SHALL NOT instruct operators to run `embedding_cli.py`, manage local embedding indices, or install `sqlite-vec` for normal bot operation

### Requirement: Similar search uses per-request timeout override
The similar search API methods SHALL use a per-request timeout that overrides the session-level default when the remote embedding backend may take longer than the general API timeout. The timeout value SHALL be sourced from `SimilarConfig.timeout`.

#### Scenario: Similar-by-id uses configurable timeout
- **WHEN** `search_similar_by_id()` is called
- **THEN** it SHALL pass a `aiohttp.ClientTimeout` with `total` equal to `SimilarConfig.timeout` to the underlying HTTP request, overriding the session-level timeout

#### Scenario: Similar-by-text uses configurable timeout
- **WHEN** `search_similar_by_text()` is called
- **THEN** it SHALL pass a `aiohttp.ClientTimeout` with `total` equal to `SimilarConfig.timeout` to the underlying HTTP request, overriding the session-level timeout

#### Scenario: Non-similar requests are unaffected
- **WHEN** any API method other than similar search is called
- **THEN** the session-level timeout of 10 seconds SHALL remain in effect

### Requirement: Similar search differentiates embedding service errors
The API client SHALL raise specific exception types for embedding-related HTTP errors so callers can distinguish them from generic API errors.

#### Scenario: Embedding service unavailable raises ApiEmbeddingError
- **WHEN** the similar API returns HTTP 502
- **THEN** the API client SHALL raise `ApiEmbeddingError` (a distinct exception class in `bot.api_client`) with the response detail as the message

#### Scenario: Embedding service timeout raises ApiEmbeddingTimeoutError
- **WHEN** the similar API returns HTTP 504
- **THEN** the API client SHALL raise `ApiEmbeddingTimeoutError` (a distinct exception class in `bot.api_client`) with the response detail as the message

#### Scenario: Generic HTTP errors still raise ApiError
- **WHEN** the similar API returns any other error status (e.g., 400)
- **THEN** the API client SHALL raise `ApiError` with the status code and detail, preserving existing behavior for error codes without dedicated exception types

## PBT Properties

