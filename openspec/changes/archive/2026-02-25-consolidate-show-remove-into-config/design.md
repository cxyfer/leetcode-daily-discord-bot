# Design: Consolidate /show_settings and /remove_channel into /config

## Context

The prior `unified-config-command` change already consolidated `/set_channel`, `/set_role`, `/set_post_time`, and `/set_timezone` into a single `/config` command with deprecated warnings. This change completes the consolidation by integrating `/show_settings` and `/remove_channel` into `/config`, then removing all deprecated commands entirely.

Current state:
- `/config` (lines 524-658): `manage_guild` required, accepts `channel/role/time/timezone/clear_role`, rejects no-param invocations
- `/show_settings` (lines 659-688): No permission check, reads settings and returns embed via `create_settings_embed()`
- `/remove_channel` (lines 791-829): `manage_guild` required, calls `delete_server_settings()` + `_reschedule_if_available()`
- `SettingsDatabaseManager` has 4 wrapper methods (`set_channel/set_role/set_post_time/set_timezone`) used only by deprecated commands
- `DEFAULT_POST_TIME`/`DEFAULT_TIMEZONE` constants are duplicated in `slash_commands_cog.py` and `schedule_manager_cog.py`

## Goals / Non-Goals

**Goals:**
- Unify show/reset/update into `/config` with mode dispatch (no-params=show, reset=True=reset, otherwise=update)
- Add Button-based confirmation for the destructive `reset` operation
- Unify update success response to use `create_settings_embed()` for visual consistency with show mode
- Remove all deprecated commands and unused DB wrappers
- Consolidate `DEFAULT_POST_TIME`/`DEFAULT_TIMEZONE` into `utils/config.py` as shared constants

**Non-Goals:**
- Splitting `/config` into subcommand groups (rejected due to Discord API limitation: commands with subcommands cannot have top-level parameters)
- Fine-grained permission differentiation between show/update/reset modes
- Adding bot channel-permission checks during config (existing behavior defers this to send time)
- Per-guild asyncio lock for concurrent `/config` invocations (last-write-wins is acceptable)

## Decisions

### DES-1: Mode dispatch order in `config_command()`

**Decision:** `reset` conflict check → show mode → time/timezone validation → update logic

**Rationale:** Placing `reset` conflict detection first prevents confusing error messages (e.g., user sends `reset:True time:abc` and gets a time-format error instead of the mutual-exclusion error). Show mode check comes before validation to avoid unnecessary processing.

**Alternatives considered:**
- Validate all inputs first, then dispatch → Rejected: produces misleading errors when reset is combined with invalid params

### DES-2: Show mode trigger condition

**Decision:** `has_update = any([channel, role, time is not None, timezone is not None, clear_role, reset])`. If `not has_update`, enter show mode.

**Rationale:** `clear_role=False` and `reset=False` are Discord defaults for bool params (indistinguishable from "not provided"). Treating `False` as "not provided" is the only correct behavior.

### DES-3: Reset with Button confirmation

**Decision:** When `reset=True` (and no other params), send an ephemeral message with a confirmation Button. Only execute `delete_server_settings()` + `_reschedule_if_available()` after the user clicks "Confirm".

**Rationale:** User requested two-step confirmation for destructive operations. The Button approach is native to Discord and avoids adding a secondary `confirm` parameter.

**Implementation:**
- Send ephemeral message: "確定要重置此伺服器的所有設定嗎？這將停止每日挑戰排程。" with Confirm/Cancel buttons
- Button custom_id: `config_reset_confirm|{server_id}` / `config_reset_cancel|{server_id}`
- Handler in `interaction_handler_cog.py` or inline View with timeout
- On confirm: `delete_server_settings()` → `_reschedule_if_available()` → edit original message to "已重置所有設定並停止排程。"
- On cancel: edit original message to "已取消重置操作。"
- View timeout (180s): disable buttons, no action taken

**Alternatives considered:**
- One-click reset (matches original `/remove_channel`) → Rejected by user decision
- `confirm: bool` parameter → Rejected: two bool params (`reset` + `confirm`) is poor UX

### DES-4: Unified embed for update success

**Decision:** After a successful update, call `create_settings_embed()` with the updated settings instead of the current plain-text summary.

**Rationale:** User requested visual consistency between show and update responses. Both modes now return the same embed format, reducing cognitive load.

**Implementation:** Reuse the same settings-to-embed logic that show mode uses. Add a "✅ 設定已更新" prefix to the embed title or send it alongside a brief text confirmation.

### DES-5: Shared default constants in `utils/config.py`

**Decision:** Add `DEFAULT_POST_TIME = "00:00"` and `DEFAULT_TIMEZONE = "UTC"` as module-level constants in `utils/config.py`. Remove the duplicated definitions from `slash_commands_cog.py` and `schedule_manager_cog.py`, replacing them with imports.

**Rationale:** Single source of truth. `ConfigManager.post_time` and `ConfigManager.timezone` properties already use these same defaults, but those require lazy initialization. Module-level constants are available at import time with no initialization dependency.

**Alternatives considered:**
- Keep separate definitions in each cog → Rejected: user requested shared constants
- Read from `ConfigManager` at runtime → Rejected: adds initialization coupling to import-time code

### DES-6: `pytz` removal from `slash_commands_cog.py`

**Decision:** Remove `import pytz` from `slash_commands_cog.py` after all deprecated commands (which used `pytz.timezone()` for validation) are deleted. The `/config` command already uses `parse_timezone()` from `utils/config.py`.

**Rationale:** `pytz` remains used in `schedule_manager_cog.py`, `leetcode.py`, `utils/ui_helpers.py`, and `utils/config.py` — only the slash cog import becomes dead code.

### DES-7: DB wrapper removal scope

**Decision:** Remove `set_channel()`, `set_role()`, `set_post_time()`, `set_timezone()` from `SettingsDatabaseManager`. Retain `get_server_settings()`, `set_server_settings()`, `get_all_servers()`, `delete_server_settings()`.

**Rationale:** grep confirms the 4 wrapper methods are only called from deprecated `/set_*` commands in `slash_commands_cog.py`. No tests, no other cogs, no scripts reference them.

### DES-8: `os` import removal from `slash_commands_cog.py`

**Decision:** After removing `DEFAULT_POST_TIME`/`DEFAULT_TIMEZONE` (which use `os.getenv`), check if `os` is still referenced. If not, remove the import.

**Rationale:** Dead import cleanup. The comment says "For os.getenv to get default POST_TIME and TIMEZONE" — once those constants move to `utils/config.py`, the import is unused.

## Risks / Trade-offs

### R1: Permission elevation for show

**Risk:** Non-admin users who previously used `/show_settings` will be blocked by `manage_guild`.
**Mitigation:** Accepted trade-off (D3 in proposal). Server settings are admin-scoped information. If community feedback demands it, a future read-only `/settings` command can be added.

### R2: Discord command propagation delay

**Risk:** After deploying, Discord clients may cache old commands for minutes to hours.
**Mitigation:** Bot startup calls `tree.sync()`. Users may need to restart Discord client in rare cases. No code-level mitigation needed.

### R3: Reset confirmation Button handler persistence

**Risk:** If bot restarts between the user seeing the confirmation Button and clicking it, the handler may be lost (if using in-memory View).
**Mitigation:** Use persistent custom_id patterns (`config_reset_confirm|{server_id}`) handled in `interaction_handler_cog.py`, ensuring they survive restarts. Alternatively, use a `discord.ui.View(timeout=180)` attached to the response — if bot restarts, the interaction will gracefully fail with "interaction failed" which is acceptable for a confirmation flow.

### R4: Concurrent reset + update race

**Risk:** Admin A sends `reset:True`, admin B sends `channel:#x` simultaneously. Final state depends on execution order.
**Mitigation:** Last-write-wins is acceptable. `reschedule_daily_challenge()` always rebuilds from current DB state, so scheduler stays consistent with DB.

## Migration Plan

1. Deploy updated code (single deployment, no phased rollout needed)
2. Bot startup triggers `tree.sync()` which removes old commands and registers updated `/config`
3. No database migration required — schema is unchanged
4. No data loss — existing server settings are preserved unless explicitly reset
5. Rollback: revert to previous commit, restart bot, `tree.sync()` re-registers old commands
