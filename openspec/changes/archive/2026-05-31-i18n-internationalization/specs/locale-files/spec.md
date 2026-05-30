## ADDED Requirements

### Requirement: Translation file structure
Each locale file SHALL be a JSON file with nested key structure using dot-notation namespaces.

#### Scenario: Key namespace organization
- **WHEN** a locale file is loaded
- **THEN** it SHALL contain top-level namespaces: `commands`, `errors`, `ui`, `llm`

#### Scenario: Nested key access
- **WHEN** the key `errors.api.processing` is looked up
- **THEN** the service SHALL traverse `errors` → `api` → `processing` in the JSON tree

### Requirement: Key coverage consistency
All locale files SHALL contain the same set of translation keys.

#### Scenario: Key parity across locales
- **WHEN** locale files are loaded
- **THEN** the set of keys in en-US.json SHALL be a superset of or equal to the set in zh-TW.json, and zh-CN.json SHALL match en-US.json

#### Scenario: Missing key detection at startup
- **WHEN** the service loads locale files and detects key mismatches
- **THEN** it SHALL log a warning listing the missing keys per locale

### Requirement: zh-TW as default locale file
`zh-TW.json` SHALL serve as the authoritative source of truth for all translation keys.

#### Scenario: New key addition
- **WHEN** a new translatable string is added to the codebase
- **THEN** the key MUST first be added to `zh-TW.json` before other locale files

### Requirement: Existing English field name preservation
Translation values for technical field names (Difficulty, Tags, Results, Source, AC Rate, Rating) in zh-TW SHALL remain in English.

#### Scenario: zh-TW embed field names
- **WHEN** embed field names are rendered in zh-TW locale
- **THEN** field names like "Difficulty", "Tags", "Source" SHALL remain in English

### Requirement: Translation value length constraints
Translation values SHALL respect Discord API length limits.

#### Scenario: Button label length
- **WHEN** a button label translation is loaded
- **THEN** its value SHALL NOT exceed 80 characters

#### Scenario: Embed field name length
- **WHEN** an embed field name translation is loaded
- **THEN** its value SHALL NOT exceed 256 characters

#### Scenario: Command description length
- **WHEN** a slash command description translation is loaded
- **THEN** its value SHALL NOT exceed 100 characters
