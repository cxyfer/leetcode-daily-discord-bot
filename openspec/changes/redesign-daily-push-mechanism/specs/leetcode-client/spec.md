## MODIFIED Requirements

### Requirement: Daily challenge fetching
The API client SHALL fetch current or historical daily challenge envelopes by LeetCode domain or canonical daily source. Canonical sources SHALL include `leetcode.com`, `leetcode.cn`, `sheep`, and `0x3f`, while scheduled server pushes SHALL use `leetcode.com`, `sheep`, or `0x3f`.

#### Scenario: Fetch today's LeetCode challenge by domain
- **WHEN** the existing manual daily flow requests domain `com` or `cn`
- **THEN** the client SHALL preserve its domain-based request behavior

#### Scenario: Fetch scheduled LeetCode challenge by source
- **WHEN** scheduled delivery requests `leetcode.com`
- **THEN** the client SHALL send `source=leetcode.com` to the daily endpoint

#### Scenario: Fetch additional daily source
- **WHEN** scheduled delivery requests `sheep` or `0x3f`
- **THEN** the client SHALL send only that canonical `source` plus any requested date and SHALL NOT send a LeetCode domain

#### Scenario: Preserve daily envelope
- **WHEN** the upstream endpoint returns a successful daily response
- **THEN** the client SHALL preserve its `date`, canonical `source`, and ordered `problems` array

#### Scenario: Historical daily challenges
- **WHEN** a date parameter is provided with a domain or source
- **THEN** the client SHALL fetch that daily challenge for the specified date

#### Scenario: Processing response retry
- **WHEN** the upstream endpoint returns HTTP 202 for a source being fetched or requiring ingestion
- **THEN** the client SHALL preserve the existing bounded processing/retry behavior

#### Scenario: Source date unavailable
- **WHEN** the upstream endpoint returns HTTP 404 for an unavailable additional-source date
- **THEN** the client SHALL expose a distinguishable not-found result so scheduled delivery can skip posting

