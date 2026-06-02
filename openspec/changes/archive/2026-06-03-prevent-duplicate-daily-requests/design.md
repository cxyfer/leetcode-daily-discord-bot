## Context

The bot currently sends daily challenges through two paths: manual slash commands and APScheduler jobs. Manual `/daily` calls delegate to shared UI helpers, while scheduled delivery creates one memory-backed job per configured server. The API client already coalesces identical in-flight HTTP requests, and interaction handling already uses an `asyncio.Lock` plus in-flight key set for duplicate LLM button requests.

The remaining gap is above the HTTP layer: concurrent scheduled jobs can still perform duplicate render/delivery work, scheduler defaults currently allow overlapping instances for the same server, and short bursts of daily requests after an in-flight request completes can re-fetch the same daily payload and history.

## Goals / Non-Goals

**Goals:**
- Prevent overlapping scheduled daily execution for the same server.
- Prevent concurrent duplicate scheduled delivery for the same server/channel/domain/date within one bot process.
- Reuse daily challenge payload data for short bursts of manual or scheduled daily requests.
- Preserve localized embed generation per request or guild.
- Keep the implementation in-memory and dependency-free for the current single-process bot runtime.

**Non-Goals:**
- Add Redis or another distributed locking service.
- Guarantee cross-process or cross-shard delivery idempotency.
- Persist daily delivery history in the database.
- Suppress legitimate manual `/daily` responses after previous requests have completed.
- Cache Discord embeds or views across locales.

## Decisions

### Use conservative APScheduler defaults for daily jobs

Set scheduled daily job defaults to `coalesce=True` and `max_instances=1` while retaining the existing misfire grace behavior. Daily challenge delivery is a once-per-day server task, so overlapping instances add risk without meaningful throughput benefit.

Alternative considered: keep `max_instances=3` and rely only on application-level guards. This would still allow unnecessary duplicate job execution and makes the scheduler less aligned with daily-delivery semantics.

### Add an in-memory scheduled delivery guard

Use an `asyncio.Lock` plus an in-flight key set for scheduled sends. The key should include at least server id, channel id, domain, and daily date. The guard should live in the scheduled delivery path rather than blocking all manual `/daily` usage.

Alternative considered: database idempotency table. This is stronger across restarts/processes, but the current runtime uses one bot process and the immediate issue is concurrent overlap, so an in-memory guard is simpler and lower risk.

### Cache daily payload data, not Discord UI objects

Introduce a short-lived daily payload cache for the fetched challenge and same-day historical problems. Embed/view construction remains per request so locale, role mention, ephemeral/public response, and interaction context remain correct.

Alternative considered: cache only `OjApiClient.get_daily()`. That helps the current challenge but still repeats history fan-out. Caching the payload directly matches the rendering workflow while still keeping the cache small.

### Reuse existing concurrency idioms

Follow existing project patterns: `asyncio.Lock` plus in-flight set from interaction handling, short TTL cache from API tags/recent submissions, and bounded fan-out with semaphores for history fetches. Avoid introducing a new service framework unless implementation needs a tiny helper module for clarity.

Alternative considered: broad refactor into a daily service layer. This may be useful later, but the current scope can remain small by placing helpers near current daily rendering code.

## Risks / Trade-offs

- In-memory guards do not survive bot restarts or coordinate across multiple processes → acceptable for current single-process runtime; document DB idempotency as a future option if deployment topology changes.
- A guard key chosen too broadly could suppress valid sends → use scheduled-only keys for delivery suppression and keep manual `/daily` responses valid.
- A guard key chosen too narrowly may miss duplicates → include server, channel, domain, and date for scheduled delivery.
- Daily payload TTL may serve stale data around day boundaries → derive cache keys from the challenge date or explicit date and keep TTL short.
- Caching payloads but rebuilding embeds still costs CPU → acceptable because the expensive duplicate work is upstream daily/history retrieval, and per-locale embed generation is required.