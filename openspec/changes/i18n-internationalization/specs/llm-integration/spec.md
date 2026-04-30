## MODIFIED Requirements

### Requirement: LLM-powered problem translation
The system SHALL translate LeetCode problem statements to the guild's resolved language using Google Gemini.

#### Scenario: Translate problem to guild locale
- **WHEN** a translation is requested for a problem
- **THEN** the LLM SHALL translate the problem statement to the guild's resolved locale language

#### Scenario: Structured output format
- **WHEN** the LLM generates a translation
- **THEN** the response SHALL conform to the Pydantic output schema with validated fields

#### Scenario: Structured output fallback
- **WHEN** structured output generation fails
- **THEN** the system SHALL fall back to parsing JSON from the plain text response, handling both markdown code blocks and raw JSON

### Requirement: LLM-powered problem inspiration
The system SHALL generate problem-solving hints and inspiration using Google Gemini, with output in the guild's resolved language.

#### Scenario: Generate inspiration in guild locale
- **WHEN** inspiration is requested for a problem
- **THEN** the LLM SHALL return structured hints in the guild's resolved locale language

#### Scenario: Hidden hint syntax
- **WHEN** inspiration contains sensitive hints
- **THEN** the output SHALL use `||` delimiter syntax for spoiler-hidden content

## ADDED Requirements

### Requirement: Locale-aware prompt templates
LLM prompt templates SHALL inject the target output language dynamically.

#### Scenario: Translation prompt with target language
- **WHEN** a translation prompt is constructed
- **THEN** it SHALL include the target language name (e.g., "繁體中文", "English", "简体中文") as a variable

#### Scenario: Inspiration prompt with output language
- **WHEN** an inspiration prompt is constructed
- **THEN** it SHALL replace the hardcoded "僅能使用繁體中文回答" with a dynamic `{output_language}` variable

#### Scenario: Language name mapping
- **WHEN** a locale code like "en-US" is used in a prompt
- **THEN** it SHALL be mapped to the human-readable language name (e.g., "English")

### Requirement: Locale-aware LLM cache
LLM cache lookups and stores SHALL include locale in the key.

#### Scenario: Cache lookup with locale
- **WHEN** a cached translation is requested
- **THEN** the lookup SHALL use (source, problem_id, locale) as the composite key

#### Scenario: Cache store with locale
- **WHEN** a new translation is cached
- **THEN** it SHALL be stored with the locale as part of the primary key
