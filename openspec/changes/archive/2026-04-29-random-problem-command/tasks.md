# Tasks: /random Command

## 1. API Client Implementation

- [x] 1.1 Add `get_random_problem()` method to OjApiClient with two-call strategy (count → random page → fetch item)
- [x] 1.2 Implement filter parameter handling (difficulty, tags, rating_min, rating_max)
- [x] 1.3 Add rating parameter auto-swap logic when min > max
- [x] 1.4 Implement zero-results handling (return domain-level no-match, not API error)
- [x] 1.5 Add error propagation for API errors (429, timeout, network failure)

## 2. Slash Command Implementation

- [x] 2.1 Add `/random` command to SlashCommandsCog with filter parameters
- [x] 2.2 Implement parameter validation (difficulty enum, rating bounds)
- [x] 2.3 Add `public` parameter handling (ephemeral vs visible)
- [x] 2.4 Implement defer pattern for Discord timeout handling
- [x] 2.5 Add error handling with filter summary in no-result messages

## 3. UI Integration

- [x] 3.1 Integrate `create_problem_embed()` for random problem display
- [x] 3.2 Integrate `create_problem_view()` for interactive buttons
- [x] 3.3 Verify button routing through InteractionHandlerCog

## 4. Testing

- [x] 4.1 Add unit tests for parameter validation and rating swap logic
- [x] 4.2 Add unit tests for `get_random_problem()` method with mocked API responses
- [x] 4.3 Add integration tests for `/random` command with various filter combinations
- [x] 4.4 Add edge case tests (no results, API errors, boundary conditions)

## 5. Documentation

- [x] 5.1 Update `config.toml.example` with any new configuration if needed
- [x] 5.2 Verify command works with both leetcode.com and leetcode.cn sources
