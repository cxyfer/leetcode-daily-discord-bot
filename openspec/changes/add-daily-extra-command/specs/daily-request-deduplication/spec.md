## MODIFIED Requirements

### Requirement: In-flight daily payload reuse
The system SHALL reuse in-flight or short-lived cached daily challenge payload data for identical daily request-target/date requests within one bot process. A request target SHALL be namespaced by kind and value so LeetCode domains (`domain:com`, `domain:cn`) and additional sources (`source:sheep`, `source:0x3f`) cannot collide.

#### Scenario: Concurrent current LeetCode daily payload requests
- **WHEN** multiple daily challenge flows request the current daily payload for the same LeetCode domain while the first request is still processing
- **THEN** the system SHALL await the same in-flight payload work instead of starting duplicate upstream daily and history fetches

#### Scenario: Concurrent current additional-source payload requests
- **WHEN** multiple `/daily_extra` flows request the current daily payload for the same additional source while the first request is still processing
- **THEN** the system SHALL await the same in-flight payload work instead of starting duplicate upstream daily fetches

#### Scenario: Short burst after payload completion
- **WHEN** a daily challenge flow requests the same request target and date shortly after a successful payload fetch
- **THEN** the system SHALL reuse the cached payload without calling the matching upstream daily API again

#### Scenario: Request target cache isolation
- **WHEN** otherwise identical requests target `domain:com`, `domain:cn`, `source:sheep`, or `source:0x3f`
- **THEN** each distinct target SHALL use a separate in-flight and cache entry
- **AND** no target SHALL receive another target's daily payload

#### Scenario: Additional sources skip LeetCode history fan-out
- **WHEN** the system builds a payload for `source:sheep` or `source:0x3f`
- **THEN** it SHALL preserve the complete daily `problems` array
- **AND** it SHALL NOT issue LeetCode historical same-day requests

#### Scenario: Existing LeetCode payload compatibility
- **WHEN** the system builds a payload for `domain:com` or `domain:cn`
- **THEN** it SHALL retain the first problem as `challenge_info`, preserve the complete `problems` array, and retain existing historical-problem behavior

#### Scenario: Locale-specific rendering remains independent
- **WHEN** two interactions render the same cached daily payload using different resolved locales
- **THEN** the system SHALL build separate localized Discord embeds and views from the shared payload

## PBT Properties

### Property: Daily target cache partition
- **INVARIANT**: Cache identity is a function of request-target namespace, target value, and explicit/resolved date
- **FALSIFICATION**: Generate the same dates across `domain:com`, `domain:cn`, `source:sheep`, and `source:0x3f` and assert only identical target/date pairs share work
