# embedding-search Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Embedding generation pipeline
The system SHALL generate vector embeddings for problem statements using a configurable Google Gemini embedding model (default: gemini-embedding-001, default dimensions: 768).

#### Scenario: Generate embeddings for a problem
- **WHEN** a problem has non-null, non-empty content
- **THEN** the system SHALL rewrite the problem statement, generate an embedding vector of the configured dimension, and store it

#### Scenario: Ineligible problem
- **WHEN** a problem has null or empty content
- **THEN** the system SHALL skip embedding generation for that problem

#### Scenario: Dimension consistency validation
- **WHEN** the embedding index is loaded for search
- **THEN** the system SHALL validate that stored vector dimensions match the configured dimension

### Requirement: Problem statement rewriting
The system SHALL rewrite problem statements into simplified form before embedding to improve search quality.

#### Scenario: Rewrite problem
- **WHEN** a problem statement contains HTML, MathJax, or verbose formatting
- **THEN** the rewriter SHALL produce a clean, simplified text version suitable for embedding

#### Scenario: Rewrite failure handling
- **WHEN** the rewriter fails or returns empty content for a problem
- **THEN** the system SHALL skip that problem and continue processing the remaining queue

### Requirement: Vector storage with sqlite-vec
The system SHALL store embedding vectors in SQLite using the sqlite-vec extension with binary float32 format.

#### Scenario: Store embedding
- **WHEN** an embedding is generated
- **THEN** the vector SHALL be stored as binary float32 (little-endian) with composite primary key (source, problem_id)

#### Scenario: Legacy JSON format support
- **WHEN** reading vectors stored in legacy JSON format
- **THEN** the system SHALL decode them correctly alongside binary format vectors

#### Scenario: Rewritten content storage
- **WHEN** a problem is rewritten and embedded
- **THEN** the rewritten content SHALL be stored in the metadata table alongside the vector

### Requirement: Similarity search
The `/similar` command SHALL find problems similar to a given problem or query using vector similarity.

#### Scenario: Search by problem
- **WHEN** a user runs `/similar` with a problem parameter
- **THEN** the system SHALL resolve the problem ID, use that problem's embedding vector to find similar problems

#### Scenario: Search by text query
- **WHEN** a user runs `/similar` with a text query
- **THEN** the system SHALL rewrite the query, generate an embedding, and find similar problems

#### Scenario: Result enrichment
- **WHEN** similar problems are found
- **THEN** the system SHALL enrich results with problem metadata (title, difficulty, tags, rating) and return rewritten_query field when applicable

#### Scenario: Display format consistency
- **WHEN** similar results are displayed via slash command or button interaction
- **THEN** both paths SHALL use the same centralized embed builder to ensure consistent formatting

#### Scenario: Over-fetch filtering
- **WHEN** similarity search is performed
- **THEN** the system SHALL over-fetch candidates (4x requested count) and filter by similarity threshold

### Requirement: Embedding CLI tooling
The `embedding_cli.py` SHALL provide commands for building, rebuilding, querying, and inspecting the embedding index.

#### Scenario: Build embeddings
- **WHEN** `--build` is specified
- **THEN** the CLI SHALL process all eligible problems without existing embeddings

#### Scenario: Rebuild embeddings
- **WHEN** `--rebuild` is specified
- **THEN** the CLI SHALL regenerate embeddings for all eligible problems

#### Scenario: Dry run cost estimation
- **WHEN** `--build --dry-run` is specified
- **THEN** the CLI SHALL report the number of problems to process without calling any APIs

#### Scenario: Show stats
- **WHEN** `--stats` is specified
- **THEN** the CLI SHALL display embedding coverage statistics

### Requirement: Batch processing
The embedding pipeline SHALL process problems in configurable batches with concurrent workers.

#### Scenario: Batch embedding generation
- **WHEN** multiple problems need embeddings
- **THEN** the system SHALL process them in batches (default size 20) with configurable concurrency for both rewriting and embedding stages

