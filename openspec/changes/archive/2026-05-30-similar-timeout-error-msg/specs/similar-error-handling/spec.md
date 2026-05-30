# similar-error-handling Specification

## Purpose
Define how `/similar` (slash command and button-triggered) communicates different failure modes to the user based on the backend HTTP response, and how client-side timeout is distinguished from server-side embedding timeout.

## ADDED Requirements

### Requirement: Differentiated similar error messages by HTTP status
The system SHALL map distinct HTTP error responses from the remote similar API endpoints to distinct localized messages so users can understand the nature of the failure.

#### Scenario: Embedding service unavailable (502)
- **WHEN** the similar API returns HTTP 502 (Bad Gateway from the embedding service)
- **THEN** the system SHALL raise `ApiEmbeddingError` from the API client layer and present a localized message indicating the embedding service is temporarily unavailable

#### Scenario: Embedding service timeout (504)
- **WHEN** the similar API returns HTTP 504 (Gateway Timeout from the embedding service)
- **THEN** the system SHALL raise `ApiEmbeddingTimeoutError` from the API client layer and present a localized message indicating the similarity computation timed out

#### Scenario: Invalid query format (400)
- **WHEN** the similar API returns HTTP 400 for a text search
- **THEN** the system SHALL present a localized message indicating the query format is invalid and suggesting a more specific problem description

#### Scenario: No embedding found for problem (404)
- **WHEN** the similar API returns HTTP 404 for a problem-based search
- **THEN** the system SHALL present a localized message indicating the problem has not been indexed for similarity search

#### Scenario: Generic API error fallback
- **WHEN** the similar API returns any other non-200 status
- **THEN** the system SHALL catch `ApiError` and present the existing generic API error message

### Requirement: Client-side timeout is distinguishable from server timeout
The system SHALL distinguish a client-side request timeout (the HTTP request to the API server did not complete within the configured timeout) from a server-side embedding timeout (HTTP 504 from the backend).

#### Scenario: Client-side timeout
- **WHEN** the similar API call raises `ApiNetworkError` due to `asyncio.TimeoutError`
- **THEN** the system SHALL present a localized message indicating the query timed out and the user should retry

#### Scenario: Server-side embedding timeout
- **WHEN** the similar API returns HTTP 504
- **THEN** the system SHALL present a different localized message indicating the embedding computation itself timed out

### Requirement: Error differentiation applies to both similar entry points
Both the `/similar` slash command and the problem-card-triggered similar button SHALL use the same error differentiation logic.

#### Scenario: Slash command error handling
- **WHEN** `/similar` slash command encounters any of the differentiated error conditions
- **THEN** it SHALL present the appropriate localized error message via `interaction.followup.send()`

#### Scenario: Button-triggered similar error handling
- **WHEN** a problem-card similar button encounters any of the differentiated error conditions
- **THEN** it SHALL present the appropriate localized error message via `interaction.followup.send()` with ephemeral visibility

### Requirement: Localized error message keys for similar failures
The i18n service SHALL provide locale-specific messages under `errors.similar.*` for each differentiated similar failure mode.

#### Scenario: Localized keys exist
- **WHEN** any supported locale is active
- **THEN** the i18n service SHALL resolve `errors.similar.invalid_query`, `errors.similar.no_embedding`, `errors.similar.embedding_unavailable`, `errors.similar.embedding_timeout`, and `errors.similar.timeout` to locale-appropriate messages
