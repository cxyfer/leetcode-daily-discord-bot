# llm-integration Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: LLM-powered problem translation
The system SHALL translate LeetCode problem statements to Traditional Chinese using Google Gemini.

#### Scenario: Translate problem
- **WHEN** a translation is requested for a problem
- **THEN** the LLM SHALL return a structured response with the translated problem statement

#### Scenario: Structured output format
- **WHEN** the LLM generates a translation
- **THEN** the response SHALL conform to the Pydantic output schema with validated fields

#### Scenario: Structured output fallback
- **WHEN** structured output generation fails
- **THEN** the system SHALL fall back to parsing JSON from the plain text response, handling both markdown code blocks and raw JSON

### Requirement: LLM-powered problem inspiration
The system SHALL generate problem-solving hints and inspiration using Google Gemini.

#### Scenario: Generate inspiration
- **WHEN** inspiration is requested for a problem
- **THEN** the LLM SHALL return structured hints without revealing the full solution

#### Scenario: Hidden hint syntax
- **WHEN** inspiration contains sensitive hints
- **THEN** the output SHALL use `||` delimiter syntax for spoiler-hidden content

#### Scenario: Field character limit
- **WHEN** inspiration fields are generated
- **THEN** each field SHALL not exceed 1000 characters

### Requirement: LLM response caching
The system SHALL cache LLM responses to minimize API costs.

#### Scenario: Cache hit
- **WHEN** a cached response exists and is within TTL (default 10 days / 604800 seconds)
- **THEN** the system SHALL return the cached response without calling the LLM API

#### Scenario: Cache miss
- **WHEN** no cached response exists or the cache has expired
- **THEN** the system SHALL call the LLM API and store the response in the cache

### Requirement: Model configuration
The system SHALL support configurable LLM model selection with separate models for standard and pro features, including custom base_url for third-party proxies.

#### Scenario: Dual model support
- **WHEN** both standard and pro model API keys are configured
- **THEN** the system SHALL initialize both `llm` and `llm_pro` instances with their respective model configurations

#### Scenario: Missing API key validation
- **WHEN** an LLM instance is created without an API key
- **THEN** the system SHALL raise a ValueError

### Requirement: Graceful LLM failure handling
The system SHALL handle LLM API failures gracefully without crashing the bot.

#### Scenario: API error
- **WHEN** the LLM API returns an error
- **THEN** the system SHALL log the error and respond to the user with an appropriate error message

