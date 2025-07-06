# LeetCode Bot Tests

## Running Tests

### Prerequisites
This project uses `uv` as the package manager. Make sure pytest and required dependencies are installed:
```bash
# Using uv (recommended)
uv pip install pytest pytest-asyncio pytest-cov

# Or using regular pip
pip install pytest pytest-asyncio pytest-cov
```

### Test Commands

1. **Run all tests:**
   ```bash
   uv run python -m pytest tests/ -v
   ```

2. **Run specific test file:**
   ```bash
   uv run python -m pytest tests/test_monthly_fetch.py -v
   ```

3. **Run with coverage report:**
   ```bash
   uv run python -m pytest tests/ -v --cov=leetcode --cov-report=term-missing
   ```

4. **Run specific test method:**
   ```bash
   uv run python -m pytest tests/test_monthly_fetch.py::TestMonthlyFetch::test_fetch_monthly_daily_challenges_success -v
   ```

5. **Run with output captured (for debugging):**
   ```bash
   uv run python -m pytest tests/ -v -s
   ```

## Test Files

- `test_monthly_fetch.py` - Tests for monthly daily challenge fetching functionality
  - Successful fetching
  - Error handling (network errors, API errors)
  - Background task processing
  - Concurrency limits
  - Task cancellation

- `test_interaction_handler.py` - Tests for Discord interaction handling and duplicate request prevention
  - Duplicate request prevention for translation and inspiration features
  - Atomic operations with asyncio.Lock
  - Proper cleanup after requests complete or error
  - Concurrent request handling
  - User and problem isolation
  - Race condition prevention

## Test Details

### test_interaction_handler.py

This test file focuses on ensuring thread-safe handling of LLM requests to prevent duplicate API calls.

#### Key Test Cases:

1. **`test_duplicate_request_prevention_translate`**
   - Verifies that duplicate translation requests from the same user are blocked
   - Ensures proper user feedback is sent

2. **`test_duplicate_request_prevention_inspire`**
   - Similar to above but for inspiration requests
   - Tests the request type isolation

3. **`test_cleanup_request`**
   - Ensures requests are properly removed from tracking set
   - Verifies `discard()` usage prevents errors on non-existent keys

4. **`test_concurrent_requests_atomic`**
   - Simulates 10 concurrent requests for the same resource
   - Verifies only one request proceeds while others are blocked
   - Tests the atomicity of the check-and-add operation

5. **`test_different_users_can_request_same_problem`**
   - Ensures different users can request the same problem simultaneously
   - Tests proper user isolation in the tracking mechanism

6. **`test_same_user_different_problems`**
   - Verifies a user can request different problems at the same time
   - Tests problem ID isolation

7. **`test_cleanup_after_error`**
   - Simulates LLM API errors
   - Ensures cleanup happens even when exceptions occur

8. **`test_lock_prevents_race_condition`**
   - Advanced test that tracks lock operations
   - Verifies the lock properly serializes access to the tracking set

#### Running Interaction Handler Tests:

```bash
# Run all interaction handler tests
uv run pytest tests/test_interaction_handler.py -v

# Run a specific test
uv run pytest tests/test_interaction_handler.py::TestInteractionHandler::test_concurrent_requests_atomic -v

# Run with debugging output
uv run pytest tests/test_interaction_handler.py -v -s
```

## Writing New Tests

When adding new tests, consider the following:

1. **Use pytest fixtures** for common setup code
2. **Mock external dependencies** (Discord API, LLM services, databases)
3. **Test both success and failure scenarios**
4. **Use `pytest.mark.asyncio` for async test functions**
5. **Keep tests focused and independent**

### Example Test Structure:

```python
@pytest.mark.asyncio
async def test_your_feature(self, cog, mock_interaction):
    # Arrange: Set up test data and mocks
    # Act: Execute the code under test
    # Assert: Verify the expected behavior
```

## Troubleshooting

- If tests fail with import errors, ensure you're running from the project root
- For async tests, make sure `pytest-asyncio` is installed
- Use `-v` flag for verbose output to see which tests are running
- Use `-s` flag to see print statements and logs during test execution