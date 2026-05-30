## MODIFIED Requirements

### Requirement: API client random problem method
The `OjApiClient` SHALL provide a `get_random_problem()` method that performs filtered random selection via the upstream native random endpoint.

#### Scenario: Native random endpoint selection
- **WHEN** `get_random_problem()` is called with filters
- **THEN** the method SHALL send a single `GET /api/v1/random` request using the normalized filter parameters and `count=1`
- **AND THEN** the method SHALL return the first item from the response `results` array when at least one problem is returned

#### Scenario: Zero results handling
- **WHEN** `get_random_problem()` is called and the API returns no matching problems
- **THEN** the method SHALL return a domain-level no-match result (not an API error)

#### Scenario: API error propagation
- **WHEN** `get_random_problem()` encounters API errors (429, timeout, network failure)
- **THEN** the method SHALL propagate standard error types (ApiRateLimitError, ApiNetworkError, ApiProcessingError)
