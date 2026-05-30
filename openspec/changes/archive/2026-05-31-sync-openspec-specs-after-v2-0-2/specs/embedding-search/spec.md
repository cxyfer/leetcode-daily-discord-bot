## MODIFIED Requirements

### Requirement: Similarity search uses the remote API backend
The `/similar` command SHALL use the remote API exposed through the application API client as its only similarity-search backend. Similar API calls SHALL use the configured similar timeout and SHALL distinguish embedding-specific error types for user-facing error handling.

#### Scenario: Search by problem
- **WHEN** a user runs `/similar` with a problem parameter
- **THEN** the system SHALL resolve the problem identifier as needed and call the API client's remote similar-by-id endpoint with the configured similar timeout

#### Scenario: Search by text query
- **WHEN** a user runs `/similar` with a text query
- **THEN** the system SHALL call the API client's remote text-search endpoint with the configured similar timeout using a POST JSON request body

#### Scenario: Shared result presentation
- **WHEN** similar problems are found from either `/similar` entry point
- **THEN** the system SHALL render the remote API response through the shared similarity-result builder

#### Scenario: Button-triggered similar uses same timeout and error contract
- **WHEN** a problem-card similar button triggers a similarity search
- **THEN** the system SHALL call the API client with the same configured timeout and differentiated embedding error handling as the slash command

### Requirement: Similar search uses per-request timeout override
The similar search API methods SHALL use a per-request timeout sourced from `SimilarConfig.timeout`, overriding the general API session timeout for similarity operations only.

#### Scenario: Similar-by-id uses configurable timeout
- **WHEN** `search_similar_by_id()` is called
- **THEN** it SHALL pass an HTTP request timeout with total equal to `SimilarConfig.timeout`

#### Scenario: Similar-by-text uses configurable timeout
- **WHEN** `search_similar_by_text()` is called
- **THEN** it SHALL pass an HTTP request timeout with total equal to `SimilarConfig.timeout`

#### Scenario: Non-similar requests are unaffected
- **WHEN** any API method other than similar search is called
- **THEN** the session-level default timeout SHALL remain in effect

### Requirement: Similar search inflight deduplication
The API client SHALL deduplicate concurrent identical similar-search requests using an inflight request key that includes the request identity and timeout contract.

#### Scenario: Identical similar requests share inflight task
- **WHEN** two concurrent similar-by-id requests have the same source, problem_id, top_k, min_similarity, and timeout
- **THEN** the API client SHALL share the same inflight task instead of issuing duplicate remote requests

#### Scenario: Different timeout uses distinct inflight task
- **WHEN** two concurrent similar requests differ only by timeout value
- **THEN** the API client SHALL treat them as distinct inflight requests

#### Scenario: Inflight entry cleanup
- **WHEN** a similar-search inflight task completes or fails
- **THEN** the API client SHALL remove the corresponding inflight entry
