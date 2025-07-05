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