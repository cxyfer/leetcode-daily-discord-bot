## Context

`SettingsDatabaseManager` currently treats `server_settings.server_id` as both the guild-settings identity and the only daily schedule identity. `ScheduleManagerCog` mirrors that model with one APScheduler job per server, and `/config` edits the same row. This ownership no longer fits three independently configurable daily sources.

The upstream daily API accepts canonical sources `leetcode.com`, `sheep`, and `0x3f` and returns a `{date, source, problems}` envelope. LeetCode normally has one problem; the additional sources may contain multiple problems. Existing overview helpers and problem interaction IDs already provide the correct multi-problem presentation owner.

The user approved a maximum of three pushes per server, exactly one per supported source. Each push has independent channel, role, time, and timezone settings. Language remains guild-wide. The user also explicitly approved removal of the legacy schema representation after backed-up, validated migration.

## Goals / Non-Goals

**Goals:**

- Enforce at most one push for each supported source per server at the database boundary.
- Preserve existing LeetCode push data and source-less `/config` behavior.
- Keep each source's channel, role, time, timezone, scheduler job, delivery guard, and failure handling independent.
- Reuse existing API, scheduler, localization, embed, and problem-button owners.
- Make migration failure recoverable through a pre-migration backup and SQLite transaction rollback.

**Non-Goals:**

- Allow multiple pushes for the same source in one server.
- Add arbitrary user-defined daily sources.
- Add persistent delivery history or cross-process idempotency.
- Duplicate upstream publishing-calendar or crawler configuration logic in the bot.
- Redesign manual `/daily` or introduce `/daily_extra` as part of this change.
- Change guild permission requirements for configuration.

## Decisions

### Normalize guild settings and daily push settings

`server_settings` remains the canonical owner of guild-wide language:

```sql
CREATE TABLE server_settings (
    server_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'zh-TW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`daily_push_settings` becomes the canonical owner of scheduled delivery configuration:

```sql
CREATE TABLE daily_push_settings (
    server_id INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('leetcode.com', 'sheep', '0x3f')),
    channel_id INTEGER NOT NULL,
    role_id INTEGER,
    post_time TEXT NOT NULL DEFAULT '00:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, source),
    FOREIGN KEY (server_id) REFERENCES server_settings(server_id) ON DELETE CASCADE
);
```

The source check plus composite primary key enforces both the source allowlist and the three-push maximum without application-only counting. Settings connections enable SQLite foreign keys so deleting guild settings removes all owned pushes.

Alternative considered: add `source` to the current single table and use `(server_id, source)` as its key. Rejected because it duplicates `language` and permits conflicting guild-wide values.

Alternative considered: add one set of columns per source. Rejected because it hard-codes repeated nullable columns and makes every new source a broad schema edit.

### Keep `/config` backward compatible and source-aware

The existing command remains the public configuration owner. It gains source choices for LeetCode, Sheep, and 0x3f plus a source-specific `remove` option.

- An update containing push fields and no source targets `leetcode.com`.
- `source:sheep` or `source:0x3f` selects that push.
- `/config` without parameters lists guild language and all configured pushes.
- `language` updates `server_settings` and does not require or select a push.
- `remove:true` requires an explicit source and deletes only that push after confirmation.
- `reset:true` retains its existing whole-guild meaning and deletes guild settings plus every push after confirmation.
- `role` and `clear_role` remain mutually exclusive.
- `remove` and `reset` cannot be combined with other updates.
- Creating a new source push requires `channel`; partial updates preserve the selected source's other fields.

The UI presents one guild-language field and one compact section per configured source. Confirmation custom IDs carry the action, guild, source when applicable, requesting user, and expiry while remaining below Discord's 100-character limit.

Alternative considered: introduce a new `/push set|list|remove` group. Rejected for this change because `/config` already owns this workflow and a new public command would add migration and documentation cost without enabling required behavior.

### Use canonical source values internally

The database, API client, cache keys, scheduler job IDs, logs, and delivery guard use canonical source values: `leetcode.com`, `sheep`, and `0x3f`. Discord choices may display `LeetCode`, `Sheep`, and `0x3f`, but they resolve to those canonical values before persistence.

The API client adds a source-oriented daily request while retaining domain-based calls used by existing manual commands. It never sends an additional source together with the LeetCode-only `domain` query parameter.

### Schedule one job per server/source pair

APScheduler job identity becomes a deterministic encoding of `(server_id, source)`. Rescheduling one source removes and recreates only that job. Whole-guild reset removes all jobs whose IDs belong to the server.

Startup loads all push rows joined with guild language and recreates every valid job. Invalid time or timezone data skips only the affected source row.

The in-process scheduled-delivery key becomes `(server_id, channel_id, source, daily_date)`. This preserves duplicate prevention for one source without suppressing another source scheduled for the same server, channel, and date.

### Reuse daily envelope and overview rendering

Scheduled delivery fetches the full `{date, source, problems}` payload. A one-problem payload uses the existing daily problem presentation. A multi-problem payload uses `create_problems_overview_embed()` and `create_problems_overview_view()` so each problem remains accessible through the established problem interaction contract.

Role mention behavior and guild locale resolution remain per push execution. Discord embeds and views are built per delivery; only payload retrieval may be reused.

An upstream 404 for an unavailable publishing date is an expected no-delivery result and is logged without posting. Existing processing/retry behavior for HTTP 202 remains in the API client. Other API, channel, and Discord failures remain isolated to the affected push.

### Migrate legacy settings with backup, validation, and rollback

Migration is detected from the legacy `server_settings` columns (`channel_id`, `role_id`, `post_time`, and `timezone`). Before destructive DDL, the bot creates a timestamped SQLite backup beside the runtime database.

Inside one SQLite transaction the migration:

1. Renames the legacy table to a temporary legacy name.
2. Creates normalized `server_settings` and `daily_push_settings` tables.
3. Copies each legacy row's guild fields into `server_settings`.
4. Copies each legacy row's push fields into `daily_push_settings` with `source = 'leetcode.com'`.
5. Verifies that the migrated guild and push counts equal the legacy row count and that no legacy server ID is missing.
6. Drops the temporary legacy table only after all checks pass.

Any failure rolls back the transaction and leaves the original database usable. The backup is not automatically deleted. New databases are created directly with normalized tables. The manual cleanup/rebuild utility recognizes both legacy and normalized inputs so cleanup cannot silently discard a legacy LeetCode push.

Alternative considered: retain old push columns as a fallback. Rejected because it creates two persistence owners and makes read/write precedence ambiguous.

## Ownership And Compatibility

| Surface | Canonical owner | Compatibility requirement |
| --- | --- | --- |
| Guild language | `server_settings` | Existing language is preserved |
| Push settings | `daily_push_settings` | Legacy row becomes `leetcode.com` |
| Configuration UX | `/config` | Source-less push edits target LeetCode |
| Job lifecycle | `ScheduleManagerCog` | One invalid source does not affect peers |
| Daily API selection | `OjApiClient` | Existing domain calls keep working |
| Multi-problem UI | `ui_helpers` overview helpers | Existing problem interaction IDs are reused |

No compatibility fallback reads legacy columns after migration. The backup is the rollback artifact; normalized tables are the only runtime source of truth.

## Risks / Trade-offs

- Schema rebuilding is higher risk than an additive table: mitigated by explicit approval, pre-migration backup, one transaction, row-count and identity validation, and migration tests.
- `/config` gains more option combinations: mitigate with a small command-input classifier and focused conflict tests instead of embedding more branches directly in the command body.
- Source names can drift between UI, database, jobs, and API: mitigate with one constants module or existing constants owner for canonical values and labels.
- Additional sources can legitimately have no payload on some dates: treat upstream 404 as expected no-delivery rather than duplicating the upstream calendar.
- Multi-problem embeds may exceed Discord limits: retain the existing overview limits and button-count constraints.

## Verification

- Schema tests prove new-table constraints and initialization assets agree.
- Migration tests prove backup creation, full legacy-to-LeetCode preservation, rollback on validation failure, and idempotent new-schema startup.
- Database CRUD tests prove independent source updates, source removal, cascade reset, and rejection of unsupported or duplicate sources.
- Command tests prove source-less LeetCode compatibility, source-specific create/update/remove, global language behavior, conflict validation, and settings display.
- Scheduler tests prove startup creates up to three independent jobs, targeted rescheduling/removal, source-scoped duplicate prevention, 404 no-delivery, and locale/role preservation.
- Delivery tests prove one-problem rendering remains unchanged and multi-problem payloads use existing overview helpers.
- Run targeted tests, full pytest, Ruff checks, and strict OpenSpec validation before completion.

## Architecture Signal

This change establishes a durable source-of-truth split between guild settings and daily push settings and changes scheduler identity from server-only to server/source. Completion should evaluate whether this decision warrants an ADR or whether the archived OpenSpec design is sufficient project authority.

