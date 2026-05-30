## 1. Configuration Layer

- [x] 1.1 Add `timeout: int = 300` field to `SimilarConfig` dataclass in `src/bot/utils/config.py`
- [x] 1.2 Update `ConfigManager.get_similar_config()` to read `timeout` from the `[similar]` TOML section
- [x] 1.3 Add `timeout = 300` to `[similar]` section in `config.toml`

## 2. API Client — Exceptions & Timeout

- [x] 2.1 Add `ApiEmbeddingError` (for HTTP 502) and `ApiEmbeddingTimeoutError` (for HTTP 504) exception classes in `src/bot/api_client.py`
- [x] 2.2 Modify `_do_request()` to raise `ApiEmbeddingError` on 502 and `ApiEmbeddingTimeoutError` on 504
- [x] 2.3 Modify `_request()` to accept optional `timeout` keyword and pass it to `_do_request()` without including it in the inflight dedup key
- [x] 2.4 Modify `search_similar_by_id()` and `search_similar_by_text()` to accept optional `timeout` parameter and pass `aiohttp.ClientTimeout(total=timeout)` to `_request()`

## 3. Cog Layer — Use Timeout & Differentiate Errors

- [x] 3.1 Update `SimilarCog.similar_command()` to read `timeout` from `SimilarConfig`, pass it to the API call, and catch `ApiEmbeddingError` / `ApiEmbeddingTimeoutError` with distinct i18n messages
- [x] 3.2 Update `InteractionHandlerCog._action_similar()` to read `timeout` from `SimilarConfig`, pass it to the API call, and catch `ApiEmbeddingError` / `ApiEmbeddingTimeoutError` with distinct i18n messages
- [x] 3.3 Map `ApiError(400)` → `errors.similar.invalid_query`, `ApiError(404)` in problem-search path → `errors.similar.no_embedding`, `ApiNetworkError` in similar context → `errors.similar.timeout`

## 4. I18n Messages

- [x] 4.1 Add `errors.similar.invalid_query`, `errors.similar.no_embedding`, `errors.similar.embedding_unavailable`, `errors.similar.embedding_timeout`, `errors.similar.timeout` keys to `src/bot/i18n/locales/zh-TW.json`
- [x] 4.2 Add corresponding English keys to `src/bot/i18n/locales/en-US.json`
- [x] 4.3 Add corresponding Chinese keys to `src/bot/i18n/locales/zh-CN.json`

## 5. Validation

- [x] 5.1 Verify `SimilarConfig()` default is 300 seconds
- [x] 5.2 Verify `config.toml` `[similar].timeout` value is read correctly
- [x] 5.3 Verify `EnvConfig.get_similar_config()` returns `SimilarConfig()` with default timeout
