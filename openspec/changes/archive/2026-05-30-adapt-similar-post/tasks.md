## 1. API client update

- [x] 1.1 Change `OjApiClient.search_similar_by_text()` to send POST `/similar` with a JSON body containing `query`, `limit`, `threshold`, and optional `source`.
- [x] 1.2 Keep `search_similar_by_id()` unchanged so problem-id similarity lookups continue to use the existing endpoint.

## 2. Test coverage

- [x] 2.1 Update or add API client tests to assert the POST method and request body for text-query similarity search.
- [x] 2.2 Add or update command-level tests to confirm `/similar` text queries still render results through the shared builder after the request shape change.
- [x] 2.3 Verify existing safe/unsafe result presentation tests still pass with the updated client contract.

## 3. Verification

- [x] 3.1 Run the targeted test suite for similarity search and command behavior.
- [x] 3.2 Review the final change set against the proposal and spec for contract alignment.
