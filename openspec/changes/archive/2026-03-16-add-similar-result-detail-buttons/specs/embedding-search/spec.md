## MODIFIED Requirements

### Requirement: Similarity search uses the remote API backend
The `/similar` command SHALL use the remote API exposed through the application API client as its only similarity-search backend. The runtime SHALL resolve similar problems by calling the API client from the packaged runtime namespace and SHALL NOT depend on local embedding indices, local vector stores, or local embedding generation workflows.

#### Scenario: Search by problem
- **WHEN** a user runs `/similar` with a problem parameter
- **THEN** the system SHALL resolve the problem identifier as needed and call the API client's remote similar-by-id endpoint to fetch results

#### Scenario: Search by text query
- **WHEN** a user runs `/similar` with a text query
- **THEN** the system SHALL call the API client's remote text-search endpoint to fetch similar problems

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

## PBT Properties

### Property: Remote-only presentation path
- **INVARIANT**: Building a similar-result response never requires local similarity lookup or eager per-result problem-detail fetches
- **FALSIFICATION**: Instrument the response-building path and assert that it uses only the existing remote similarity payload plus the existing lazy `view` interaction for full details

### Property: Slash clamp independence from UI cap
- **INVARIANT**: Slash `/similar` input normalization stays bounded by its existing fetch clamp even though the detail-button render cap is 25
- **FALSIFICATION**: Generate arbitrary slash `top_k` inputs and assert that the remote similarity fetch limit remains clamped to the slash-command policy rather than the render-time button cap
