## 1. Native random endpoint adoption

- [x] 1.1 Update `OjApiClient.get_random_problem()` to call the upstream `GET /api/v1/random` endpoint with the existing random filters
- [x] 1.2 Preserve rating normalization, parameter omission for `None`, and `count=1` in the request payload
- [x] 1.3 Parse the response by returning the first item from `results` or `None` when the array is empty
- [x] 1.4 Update or add tests covering request shape, response parsing, and zero-result handling
- [x] 1.5 Verify `/random` command behavior remains unchanged for Discord users
