## ADDED Requirements

### Requirement: Translation file structure
Each locale file SHALL be a JSON file with nested key structure for translatable runtime strings.

#### Scenario: Key namespace organization
- **WHEN** a locale file is loaded
- **THEN** it SHALL contain top-level namespaces for command metadata, errors, UI text, and LLM text

#### Scenario: Nested key access
- **WHEN** the key `errors.api.processing` is looked up
- **THEN** the service SHALL traverse `errors` then `api` then `processing` in the JSON tree

### Requirement: Key coverage consistency
Locale files SHALL maintain consistent translation key coverage across supported locales.

#### Scenario: Key parity across locales
- **WHEN** locale files are loaded
- **THEN** en-US and zh-CN SHALL contain the same translation key set as zh-TW

#### Scenario: Missing key detection at startup
- **WHEN** the service detects key mismatches while loading locale files
- **THEN** it SHALL log a warning listing the missing keys per locale

### Requirement: zh-TW source-of-truth locale
`zh-TW.json` SHALL serve as the authoritative source of truth for translation keys.

#### Scenario: New key addition
- **WHEN** a new translatable string is added to the codebase
- **THEN** the key MUST first be added to `zh-TW.json` before other locale files

### Requirement: Preserved technical field names
Translation values for technical problem metadata fields SHALL preserve established English labels where required.

#### Scenario: zh-TW embed field names
- **WHEN** embed field names are rendered in zh-TW locale
- **THEN** field names such as `Difficulty`, `Tags`, `Source`, `AC Rate`, and `Rating` SHALL remain in English

### Requirement: Discord translation length constraints
Translation values SHALL respect Discord API length limits for their target UI surface.

#### Scenario: Button label length
- **WHEN** a button label translation is loaded
- **THEN** its value SHALL NOT exceed 80 characters

#### Scenario: Embed field name length
- **WHEN** an embed field name translation is loaded
- **THEN** its value SHALL NOT exceed 256 characters

#### Scenario: Command description length
- **WHEN** a slash command description translation is loaded
- **THEN** its value SHALL NOT exceed 100 characters
