## Context

The bot currently uses four separate slash commands (`/set_channel`, `/set_role`, `/set_post_time`, `/set_timezone`) for server configuration. This requires multiple interactions for initial setup and only supports IANA timezone names (e.g., `Asia/Taipei`), not the more intuitive UTC offset format (e.g., `UTC+8`).

Key integration points:
- `cogs/slash_commands_cog.py:337-496` — current `/set_*` commands with duplicated validation/response patterns
- `utils/database.py:84-206` — `set_server_settings()` UPSERT + individual `set_*` wrappers (read-merge-write)
- `cogs/schedule_manager_cog.py:85` — directly calls `pytz.timezone(timezone_str)` for CronTrigger
- `show_settings` command references `/set_channel` in its empty-state message

## Goals / Non-Goals

**Goals:**
- Unify all server configuration into a single `/config` command with optional parameters
- Support UTC offset timezone format (`UTC+8`, `UTC-5`, `UTC+5:30`) alongside IANA names
- Deprecate old `/set_*` commands with warnings (remove in next release)
- Add timezone autocomplete (UTC offsets + popular IANA zones)
- Support role clearing (set role to None)
- Auto-pad single-digit hour in time input (`8:00` → `08:00`)

**Non-Goals:**
- Database schema migration (TEXT timezone column already sufficient)
- Converting existing IANA timezone records to UTC offset format
- Adding new configuration fields (language, difficulty filter, etc.)
- Implementing optimistic concurrency control for concurrent admin updates

## Decisions

### D1: `parse_timezone()` location — `utils/config.py`

**Rationale:** Both `slash_commands_cog.py` (validation) and `schedule_manager_cog.py` (scheduling) need timezone parsing. Placing it in `utils/config.py` colocates it with existing configuration utilities and avoids a new file for a single function.

**Alternatives considered:**
- `utils/timezone.py` — rejected; single-function module adds unnecessary file overhead
- Inline in cog — rejected; violates DRY since scheduler also needs it

### D2: Timezone object type — `datetime.timezone` for offsets, `pytz.timezone` for IANA

**Rationale:** `datetime.timezone(timedelta(minutes=N))` provides explicit fixed-offset semantics with no DST ambiguity. APScheduler 3.11.2 `CronTrigger` accepts both `datetime.timezone` and `pytz.tzinfo`. IANA names continue using `pytz.timezone()` for DST-aware behavior.

**Alternatives considered:**
- `pytz.FixedOffset` for all offsets — rejected; unnecessary coupling to pytz internals
- `zoneinfo.ZoneInfo` for IANA — rejected; project already depends on pytz, mixing adds complexity

### D3: Legacy command handling — Deprecation warnings for one release cycle

**Rationale:** Gradual migration reduces disruption for existing server admins. Old commands will emit a deprecation notice pointing to `/config` while remaining functionally equivalent. Removal planned for next minor version.

**Alternatives considered:**
- Immediate removal — rejected; breaking change without transition period
- Keep both indefinitely — rejected; duplicate maintenance burden and behavior drift risk

### D4: Storage strategy — Store original timezone string, parse at read time

**Rationale:** Preserving user input (e.g., `UTC+8` vs `Etc/GMT-8`) makes `show_settings` display more intuitive. All read paths must use `parse_timezone()` to convert stored string to `tzinfo`.

**Implementation:** `schedule_manager_cog.py:85` changes from `pytz.timezone(timezone_str)` to `parse_timezone(timezone_str)`.

### D5: Validation strategy — Validate all parameters before any DB write

**Rationale:** Atomic validation prevents partial update states. If timezone is invalid but channel is valid, neither should be written.

**Flow:**
1. Collect all provided parameters
2. Validate each (channel existence, time format, timezone format, role)
3. If any fails → return error, no DB mutation
4. Merge validated params with existing settings
5. Single `set_server_settings()` call

### D6: Time format — Accept `H:MM`, normalize to `HH:MM` before storage

**Rationale:** Users frequently type `8:00` instead of `08:00`. Auto-padding is user-friendly and ensures canonical storage format. Validation: `0 <= hour <= 23`, `0 <= minute <= 59`.

### D7: Role clearing — Sentinel value via dedicated `clear_role` boolean parameter

**Rationale:** Discord's `app_commands` cannot pass `None` for an optional `Role` parameter (omitting it means "don't change"). A separate `clear_role: bool = False` parameter explicitly signals intent to remove the role mention.

**Alternatives considered:**
- Magic role value — rejected; no clean way to represent "clear" in Discord's Role type
- Separate `/config_clear_role` command — rejected; defeats the purpose of unification

### D8: Timezone autocomplete — UTC offsets + top IANA zones

**Rationale:** Timezone strings are error-prone. Autocomplete with common UTC offsets (`UTC-12` through `UTC+14` integers + half-hour offsets like `UTC+5:30`, `UTC+9:30`) and ~10 popular IANA zones (`Asia/Taipei`, `Asia/Tokyo`, `America/New_York`, `Europe/London`, etc.) covers most users.

**Implementation:** `@config_command.autocomplete("timezone")` with fuzzy matching on user input.

## Risks / Trade-offs

**R1: Mixed timezone formats in DB** → All read paths must use `parse_timezone()`. Direct `pytz.timezone()` calls on raw DB strings will crash for `UTC+8` records. Mitigation: grep and replace all direct `pytz.timezone(settings['timezone'])` calls.

**R2: Concurrent admin updates (last-write-wins)** → Two admins running `/config` simultaneously could cause lost updates due to read-merge-write pattern. Mitigation: Accepted for MVP; short-term risk is low (config changes are rare). Document as known limitation.

**R3: Deprecation transition confusion** → Users may be confused seeing both old and new commands during transition. Mitigation: Old commands emit clear deprecation message with exact `/config` equivalent syntax.

**R4: Invalid legacy timezone strings** → Manual DB edits or corruption could produce unparseable timezone strings, causing schedule creation failure. Mitigation: `add_server_schedule` should catch `ValueError` from `parse_timezone()` and log error without crashing the scheduler loop.

**R5: `UTC+0` vs `UTC` semantic difference** → Both should produce equivalent scheduling behavior but are stored as different strings. Mitigation: Document that these are equivalent; `parse_timezone()` handles both correctly (IANA path for "UTC", offset path for "UTC+0").

## Migration Plan

**Deployment:**
1. Add `parse_timezone()` to `utils/config.py`
2. Update `schedule_manager_cog.py` to use `parse_timezone()` instead of `pytz.timezone()`
3. Add `/config` command with all parameters + autocomplete + `clear_role`
4. Add deprecation warnings to existing `/set_*` commands
5. Update `show_settings` empty-state message to reference `/config`
6. Update CHANGELOG.md with deprecation notice

**Rollback:** Revert to previous version; DB data remains compatible since timezone column is TEXT and IANA strings still work.

**Next release:** Remove `/set_*` commands and their DB wrapper methods (`set_channel`, `set_role`, `set_post_time`, `set_timezone`).

## PBT Properties

| Category | Invariant | Falsification Strategy |
|---|---|---|
| Round-trip | `parse_timezone(tz_str).utcoffset(None)` matches encoded offset for all valid UTC offset strings | Generate offset strings in supported shapes, compare parsed utcoffset against numeric input |
| Round-trip | `parse_timezone(tz_str)` output is always accepted by `CronTrigger(timezone=...)` | Generate valid timezone strings across both families, instantiate CronTrigger, fail on any TypeError |
| Round-trip | DB write/read cycle: stored string re-parses to equivalent tzinfo | Write timezone, read back, compare next_fire_time from both |
| Idempotency | `/config` with same params N times → same DB state (excluding `updated_at`) | Apply random valid payloads repeatedly, compare config columns |
| Idempotency | `"8:00"` and `"08:00"` produce identical stored value `"08:00"` | Apply both forms, assert DB value equality |
| Idempotency | Role clearing N times keeps role NULL without side effects | Set role → clear → clear → assert NULL persists |
| Invariant | `channel_id` is never NULL after any successful `/config` call | Mix valid/invalid command sequences, assert channel_id after each |
| Atomicity | If any parameter fails validation, entire DB record unchanged | Submit commands with 3 valid + 1 invalid param, assert no partial commit |
| Bounds | UTC offset accepted in [-12:00, +14:00], rejected outside | Test UTC-12:00 (accept), UTC+14:00 (accept), UTC-12:01 (reject), UTC+14:01 (reject) |
| Bounds | Time accepted in [00:00, 23:59], rejected outside | Test 00:00 (accept), 23:59 (accept), 24:00 (reject), 12:60 (reject) |
| Equivalence | `UTC+0`, `UTC-0`, and `UTC` produce equivalent scheduling behavior | Compare utcoffset and CronTrigger next_fire_time across all three |
| Monotonicity | Successful `/config` strictly increases `updated_at` | Rapid sequential updates, assert timestamp ordering |
| Monotonicity | Failed validation does not advance `updated_at` | Interleave invalid calls, snapshot before/after |
