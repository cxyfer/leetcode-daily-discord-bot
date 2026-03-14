## MODIFIED Requirements

### Requirement: Similarity search uses the remote API backend
The `/similar` command SHALL use the remote API exposed through the application API client as its only similarity-search backend. The runtime SHALL resolve similar problems by calling the API client from the packaged runtime namespace and SHALL NOT depend on local embedding indices, local vector stores, or local embedding generation workflows.

#### Scenario: Search by problem
- **WHEN** a user runs `/similar` with a problem parameter
- **THEN** the system SHALL resolve the problem identifier as needed and call the API client's remote similar-by-id endpoint to fetch results

#### Scenario: Search by text query
- **WHEN** a user runs `/similar` with a text query
- **THEN** the system SHALL call the API client's remote text-search endpoint to fetch similar problems

#### Scenario: Result enrichment and presentation
- **WHEN** similar problems are found
- **THEN** the system SHALL render the remote API response through the shared embed builder used by the similarity feature

#### Scenario: Runtime ownership
- **WHEN** runtime code performs similarity search after the source layout is reorganized under `src/bot/`
- **THEN** ownership SHALL remain within packaged runtime modules such as `bot.api_client` and `bot.cogs.similar_cog`

### Requirement: No local similarity maintenance workflow
The repository SHALL NOT document or require local embedding build, rebuild, query, or vector-storage workflows for `/similar`.

#### Scenario: Documentation guidance
- **WHEN** runtime or developer documentation describes `/similar`
- **THEN** it SHALL describe the feature as remote-only and SHALL NOT instruct operators to run `embedding_cli.py`, manage local embedding indices, or install `sqlite-vec` for normal bot operation
