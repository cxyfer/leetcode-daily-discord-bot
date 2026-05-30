## Why

Upstream changed text-based `/similar` search from GET query parameters to a POST JSON body, and the current bot will stop matching the deployed API contract once the upstream server is on the new nightly release. This change keeps text-query similarity search working for long queries while preserving the existing problem-id search flow.

## What Changes

- Update the bot's text-query similarity request to use POST with a JSON body.
- Keep problem-id similarity search on the existing by-id endpoint.
- Preserve the current `/similar` Discord command interface and result presentation.
- Update or add tests to cover the new request shape and response handling.

## Capabilities

### Modified Capabilities
- `embedding-search`: text-query similarity search now uses the upstream POST JSON contract instead of GET query parameters.

## Impact

- `src/bot/api_client.py` request construction for `search_similar_by_text()`.
- `tests/` coverage for text similarity requests and command behavior.
- Upstream API compatibility for deployments that use the nightly `oj-api-rs` contract.
