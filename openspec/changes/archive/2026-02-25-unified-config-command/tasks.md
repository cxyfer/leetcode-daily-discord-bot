## 1. Timezone Parsing Utility

- [x] 1.1 Add `parse_timezone(tz_string: str) -> tzinfo` function to `utils/config.py`: try `pytz.timezone()` first, then regex `^UTC([+-])(\d{1,2})(?::?([0-5]\d))?$` for UTC offset, return `datetime.timezone(timedelta(minutes=N))` for offsets; raise `ValueError` for invalid input; validate offset range -720 to +840 minutes
- [x] 1.2 Add `import re` and `from datetime import timezone, timedelta` to `utils/config.py` imports

## 2. Schedule Manager Integration

- [x] 2.1 In `cogs/schedule_manager_cog.py:85`, replace `pytz.timezone(timezone_str)` with `parse_timezone(timezone_str)` imported from `utils/config`
- [x] 2.2 Wrap `parse_timezone()` call in `add_server_schedule` with try/except `ValueError`, log error and skip scheduling for that server on failure (do not crash scheduler loop)

## 3. Unified Config Command

- [x] 3.1 Add `/config` command to `cogs/slash_commands_cog.py` with `@app_commands.command(name="config")`, `@guild_only()`, `@has_permissions(manage_guild=True)`, parameters: `channel: Optional[TextChannel]`, `role: Optional[Role]`, `time: Optional[str]`, `timezone: Optional[str]`, `clear_role: bool = False`
- [x] 3.2 Implement validation-first flow: check `clear_role` + `role` mutual exclusion → validate time format (accept `H:MM`, normalize to `HH:MM` via zero-pad) → validate timezone via `parse_timezone()` → check channel required on first setup (no existing settings and no channel param) → check at least one param provided
- [x] 3.3 Implement merge logic: read existing settings, overlay validated params, call `set_server_settings()` once; if `clear_role=True`, set `role_id=None` in merged params
- [x] 3.4 Implement success response: ephemeral message showing channel mention (fallback to `ID: {id}`), role mention or "未設定", post_time, timezone
- [x] 3.5 Call `_reschedule_if_available(server_id, "config")` after successful DB update
- [x] 3.6 Add error handler `config_command_error` for `MissingPermissions` and `NoPrivateMessage`

## 4. Timezone Autocomplete

- [x] 4.1 Define timezone choices list: integer UTC offsets from UTC-12 to UTC+14, half-hour offsets (UTC+3:30, UTC+4:30, UTC+5:30, UTC+5:45, UTC+6:30, UTC+8:45, UTC+9:30, UTC+10:30, UTC+12:45), and popular IANA zones (UTC, Asia/Taipei, Asia/Tokyo, Asia/Shanghai, Asia/Kolkata, America/New_York, America/Los_Angeles, America/Chicago, Europe/London, Europe/Berlin)
- [x] 4.2 Add `@config_command.autocomplete("timezone")` method that filters choices by case-insensitive substring match on user input, return up to 25 `app_commands.Choice` items

## 5. Legacy Command Deprecation

- [x] 5.1 In each of `set_channel_command`, `set_role_command`, `set_post_time_command`, `set_timezone_command`: append deprecation warning to success response message — format: `"\n\n⚠️ 此指令即將廢棄，請改用 /config <equivalent params>"` with the specific `/config` equivalent
- [x] 5.2 Update `show_settings_command` empty-state message (line ~507) from `使用 /set_channel 開始設定` to `使用 /config channel:<頻道> 開始設定`

## 6. Deprecation Error Messages in Legacy Commands

- [x] 6.1 In `set_role_command` and `set_post_time_command` and `set_timezone_command`: update the "請先使用 `/set_channel`" error message to reference `/config channel:<頻道>` instead

## 7. Cleanup and Validation

- [x] 7.1 Grep codebase for remaining direct `pytz.timezone(` calls on user-stored timezone strings; ensure all are replaced with `parse_timezone()`
- [x] 7.2 Verify `import pytz` in `slash_commands_cog.py` is still needed (used by deprecated commands' timezone validation); keep it for transition period
