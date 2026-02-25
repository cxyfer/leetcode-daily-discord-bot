## 1. Shared Default Constants

- [x] 1.1 In `utils/config.py`, add module-level constants after imports: `DEFAULT_POST_TIME = "00:00"` and `DEFAULT_TIMEZONE = "UTC"` — these are plain string literals, not reading from env or ConfigManager
- [x] 1.2 In `cogs/slash_commands_cog.py`, remove lines 30-31 (`DEFAULT_POST_TIME = os.getenv(...)` / `DEFAULT_TIMEZONE = os.getenv(...)`), add `from utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE` to imports, remove `import os` if no longer referenced
- [x] 1.3 In `cogs/schedule_manager_cog.py`, remove lines 16-17 (`DEFAULT_POST_TIME = os.getenv(...)` / `DEFAULT_TIMEZONE = os.getenv(...)`), add `from utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE` to imports, remove `import os` if no longer referenced

## 2. Extract Shared Reschedule Helper

- [x] 2.1 In `bot.py` `main()` function, after `await load_extensions()`, add a helper method to the bot instance: `bot.reschedule_daily_challenge = _create_reschedule_helper(bot)` — this function takes `(server_id: int, context: str = "")`, calls `bot.get_cog("ScheduleManagerCog").reschedule_daily_challenge(server_id)` with a warning log if cog not found
- [x] 2.2 Define `_create_reschedule_helper(bot)` as a module-level function in `bot.py` that returns an async closure matching the signature above, replicating the exact logic from `SlashCommandsCog._reschedule_if_available`
- [x] 2.3 In `cogs/slash_commands_cog.py`, replace `_reschedule_if_available` method body to delegate to `self.bot.reschedule_daily_challenge(server_id, context)`, remove the `schedule_cog` property if no longer used elsewhere in the cog

## 3. Extend /config — Show Mode

- [x] 3.1 In `cogs/slash_commands_cog.py` `config_command`, replace the "no params → error" block: compute `has_update = any([channel, role, time is not None, timezone is not None, clear_role, reset])`, if `not has_update` enter show mode
- [x] 3.2 Show mode implementation: call `self.bot.db.get_server_settings(server_id)`, if no settings or no `channel_id` respond ephemeral `"尚未設定 LeetCode 每日挑戰頻道。使用 /config channel:<頻道> 開始設定。"`, otherwise resolve channel mention (`self.bot.get_channel(channel_id).mention` or fallback `"未知頻道 (ID: {id})"`), role mention (guild.get_role or `"未設定"`), post_time/timezone with DEFAULT fallbacks, call `create_settings_embed(guild.name, channel_mention, role_mention, post_time, timezone)`, respond with `embed=embed, ephemeral=True`
- [x] 3.3 Add `from utils.ui_helpers import create_settings_embed` to `slash_commands_cog.py` imports

## 4. Extend /config — Reset Mode with Button Confirmation

- [x] 4.1 Add `reset: bool = False` parameter to `config_command` signature, with `@app_commands.describe(reset="重置所有設定並停止排程（需確認）")`
- [x] 4.2 Insert reset conflict check at the START of `config_command` (before show mode check): if `reset` and any of `[channel, role, time is not None, timezone is not None, clear_role]`, respond ephemeral `"`reset` 不可與其他設定參數同時使用。"` and return
- [x] 4.3 After show mode check, add reset mode block: if `reset` is True, call `self.bot.db.get_server_settings(server_id)`, if no settings respond ephemeral `"此伺服器尚未設定，無需重置。"` and return
- [x] 4.4 In reset mode: resolve channel/role mentions (same logic as show mode), build settings preview embed via `create_settings_embed()`, compute `exp_unix = int(time.time()) + 180`, build two buttons:
  - Confirm: `label="確認重置"`, `style=ButtonStyle.danger`, `custom_id=f"config_reset_confirm|{server_id}|{interaction.user.id}|{exp_unix}"`
  - Cancel: `label="取消"`, `style=ButtonStyle.secondary`, `custom_id=f"config_reset_cancel|{server_id}|{interaction.user.id}|{exp_unix}"`
- [x] 4.5 Send ephemeral message with `content="⚠️ 確定要重置此伺服器的所有設定嗎？這將停止每日挑戰排程。"`, `embed=settings_preview_embed`, `view=view`
- [x] 4.6 Add `import time` to `slash_commands_cog.py` if not already present

## 5. Reset Button Handler in InteractionHandlerCog

- [x] 5.1 In `cogs/interaction_handler_cog.py` `on_interaction` method, add routing branch: if `custom_id.startswith("config_reset_confirm|")` or `custom_id.startswith("config_reset_cancel|")`, call `await self._handle_config_reset(interaction)`
- [x] 5.2 Implement `_handle_config_reset(self, interaction)`:
  - Parse custom_id by `split("|")`, validate exactly 4 parts `[action, guild_id, user_id, exp_unix]`, wrap in try/except for malformed IDs → respond ephemeral `"無效的操作。"` and return
  - Check `interaction.guild is None` → respond ephemeral `"此操作僅能在伺服器中使用。"` and return
  - Check `int(user_id) != interaction.user.id` → respond ephemeral `"此操作僅限原發起者使用。"` and return
  - Check `int(time.time()) > int(exp_unix)` → respond ephemeral `"此確認已過期，請重新使用 /config reset:True。"` and return
  - If action is `config_reset_cancel`: `await interaction.response.edit_message(content="已取消重置操作。", embed=None, view=None)` and return
  - If action is `config_reset_confirm`:
    - Re-check `interaction.user.guild_permissions.manage_guild` → if False, respond ephemeral `"您需要「管理伺服器」權限才能執行此操作。"` and return
    - Call `self.bot.db.delete_server_settings(int(guild_id))`
    - Call `await self.bot.reschedule_daily_challenge(int(guild_id), "config_reset")`
    - `await interaction.response.edit_message(content="✅ 已重置所有設定並停止排程。", embed=None, view=None)`
- [x] 5.3 Add `import time` to `interaction_handler_cog.py` imports
- [x] 5.4 Add `from utils.logger import get_commands_logger` is already present; add logging for reset confirm/cancel actions at INFO level: `self.logger.info(f"Config reset {'confirmed' if confirm else 'cancelled'} for guild {guild_id} by user {interaction.user.id}")`

## 6. Update Success Response to Embed

- [x] 6.1 In `cogs/slash_commands_cog.py` `config_command`, replace the plain-text success response (lines ~620-635) with: resolve channel/role mentions from `base` dict (same pattern as show mode), call `create_settings_embed(interaction.guild.name, ch_display, role_display, base['post_time'], base['timezone'])`, respond with `content="✅ 設定已更新", embed=embed, ephemeral=True`

## 7. Remove Deprecated Commands

- [x] 7.1 In `cogs/slash_commands_cog.py`, delete `set_channel_command` method and its `set_channel_error` error handler
- [x] 7.2 Delete `set_role_command` method and its `set_role_error` error handler
- [x] 7.3 Delete `set_post_time_command` method and its `set_post_time_error` error handler
- [x] 7.4 Delete `set_timezone_command` method and its `set_timezone_error` error handler
- [x] 7.5 Delete `show_settings_command` method (no error handler)
- [x] 7.6 Delete `remove_channel_command` method and its `remove_channel_error` error handler

## 8. Remove Unused DB Wrapper Methods

- [x] 8.1 In `utils/database.py` `SettingsDatabaseManager`, delete methods: `set_channel()`, `set_role()`, `set_post_time()`, `set_timezone()`
- [x] 8.2 Verify via grep that no other code references these method names — expected result: zero references after step 7

## 9. Import Cleanup

- [x] 9.1 In `cogs/slash_commands_cog.py`: remove `import pytz` (no longer used after deprecated commands removed — `/config` uses `parse_timezone` from utils)
- [x] 9.2 In `cogs/slash_commands_cog.py`: remove `import os` if no remaining references
- [x] 9.3 Remove any now-unused imports from `cogs/slash_commands_cog.py` (verify with a quick grep for each import symbol)
- [x] 9.4 In `cogs/slash_commands_cog.py`: verify `DEFAULT_POST_TIME`, `DEFAULT_TIMEZONE` imports from `utils.config` are present (from task 1.2)

## 10. Verification

- [x] 10.1 Grep codebase for `show_settings`, `remove_channel`, `set_channel`, `set_role`, `set_post_time`, `set_timezone` command registrations — expected: zero matches outside of openspec/, CLAUDE.md, README.md
- [x] 10.2 Grep `utils/database.py` for `def set_channel`, `def set_role`, `def set_post_time`, `def set_timezone` — expected: zero matches
- [x] 10.3 Grep for hardcoded `"00:00"` or `"UTC"` used as scheduling defaults outside `utils/config.py` — expected: zero matches (ConfigManager properties should reference the constants or be independently defined)
- [x] 10.4 Verify `cogs/slash_commands_cog.py` exports exactly 5 slash commands: `daily`, `daily_cn`, `problem`, `recent`, `config`
- [x] 10.5 Verify all `/config` response paths use `ephemeral=True`
- [x] 10.6 Verify reset button custom_id format: `config_reset_{confirm|cancel}|{guild_id}|{user_id}|{exp_unix}`
