## MODIFIED Requirements

### Requirement: LLM-powered problem translation
The system SHALL translate problem statements to the resolved locale language using Google Gemini.

#### Scenario: Translate problem to resolved locale
- **WHEN** a translation is requested for a problem
- **THEN** the LLM SHALL return a structured response translated to the resolved locale language

#### Scenario: Structured output format
- **WHEN** the LLM generates a translation
- **THEN** the response SHALL conform to the Pydantic output schema with validated fields

#### Scenario: Structured output fallback
- **WHEN** structured output generation fails
- **THEN** the system SHALL fall back to parsing JSON from the plain text response, handling both markdown code blocks and raw JSON

### Requirement: LLM-powered problem inspiration
The system SHALL generate problem-solving hints and inspiration using Google Gemini, with output in the resolved locale language.

#### Scenario: Generate inspiration in resolved locale
- **WHEN** inspiration is requested for a problem
- **THEN** the LLM SHALL return structured hints in the resolved locale language without revealing the full solution

#### Scenario: Hidden hint syntax
- **WHEN** inspiration contains sensitive hints
- **THEN** the output SHALL use `||` delimiter syntax for spoiler-hidden content

#### Scenario: Field character limit
- **WHEN** inspiration fields are generated
- **THEN** each field SHALL not exceed 1000 characters

### Requirement: LLM response caching
The system SHALL cache LLM responses by source, problem, and locale to minimize API costs without cross-language cache pollution.

#### Scenario: Cache hit by locale
- **WHEN** a cached response exists for the same source, problem_id, locale, and is within TTL
- **THEN** the system SHALL return the cached response without calling the LLM API

#### Scenario: Cache miss for different locale
- **WHEN** a cached response exists for the same source and problem_id but a different locale
- **THEN** the system SHALL treat the request as a cache miss

#### Scenario: Cache store with locale
- **WHEN** a new LLM response is cached
- **THEN** the system SHALL store it with locale as part of the cache key

## ADDED Requirements

### Requirement: Locale-aware prompt templates
LLM prompt templates SHALL inject the target output language dynamically.

#### Scenario: Translation prompt target language
- **WHEN** a translation prompt is constructed for locale `en-US`
- **THEN** it SHALL include the human-readable target language `English`

#### Scenario: Inspiration prompt target language
- **WHEN** an inspiration prompt is constructed for locale `zh-CN`
- **THEN** it SHALL instruct the LLM to answer in Simplified Chinese

#### Scenario: Traditional Chinese default language
- **WHEN** no locale-specific language name is available
- **THEN** the prompt SHALL use Traditional Chinese as the default output language
