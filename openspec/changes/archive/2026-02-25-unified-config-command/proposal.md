# Proposal: Unified Config Command

## Context

### User Need
使用者反映目前的設定指令過於繁瑣,需要執行多個獨立的指令 (`/set_channel`, `/set_role`, `/set_post_time`, `/set_timezone`) 才能完成伺服器設定。此外,時區設定僅支援 IANA 時區名稱格式 (如 `Asia/Taipei`),不支援更直觀的 UTC offset 格式 (如 `UTC+8`)。

### Current Implementation Constraints

**Discovered Constraints from Codebase:**

1. **Command Structure** (cogs/slash_commands_cog.py:337-496)
   - 現有四個獨立的設定指令: `set_channel`, `set_role`, `set_post_time`, `set_timezone`
   - 每個指令都需要 `manage_guild` 權限
   - 除了 `set_channel` 外,其他指令都要求先設定 channel
   - 每次設定後都會觸發 `_reschedule_if_available()` 重新排程

2. **Database Schema** (utils/database.py:38-48)
   - `server_settings` 表結構:
     - `server_id` (INTEGER PRIMARY KEY)
     - `channel_id` (INTEGER NOT NULL)
     - `role_id` (INTEGER, nullable)
     - `post_time` (TEXT DEFAULT '00:00')
     - `timezone` (TEXT DEFAULT 'UTC')
   - `channel_id` 是必填欄位,其他設定都依賴它存在

3. **Timezone Validation** (cogs/slash_commands_cog.py:460-467)
   - 使用 `pytz.timezone()` 驗證時區
   - 僅接受 IANA 時區名稱 (如 `Asia/Taipei`, `UTC`)
   - 不支援 UTC offset 格式 (如 `UTC+8`, `UTC-5`)

4. **Scheduler Integration** (cogs/schedule_manager_cog.py:83-88)
   - 使用 `pytz.timezone(timezone_str)` 建立 timezone 物件
   - 傳遞給 APScheduler 的 `CronTrigger`
   - 必須是有效的 pytz timezone 物件

5. **Time Format Validation** (cogs/slash_commands_cog.py:414-423)
   - 時間格式: `HH:MM` (24小時制)
   - 驗證範圍: 0 <= hour <= 23, 0 <= minute <= 59

6. **Database Operations Pattern** (utils/database.py:123-206)
   - 所有 `set_*` 方法都會:
     1. 讀取現有設定
     2. 合併新值與舊值
     3. 呼叫 `set_server_settings()` 更新
   - 這種模式確保部分更新不會覆蓋其他欄位

## Requirements

### REQ-1: Unified Configuration Command
**Priority:** High
**Scenario:** 使用者執行單一指令即可設定所有伺服器配置

**Acceptance Criteria:**
- 新增 `/config` 指令,接受多個可選參數
- 參數包括: `channel`, `role`, `time`, `timezone`
- 所有參數都是可選的,使用者可以只設定需要變更的項目
- 保持與現有指令相同的權限要求 (`manage_guild`)
- 保持與現有指令相同的驗證邏輯

**Constraints:**
- 必須保持向後相容:現有的 `/set_*` 指令應繼續運作
- `channel` 參數在首次設定時為必填,後續更新時可選
- 驗證邏輯必須與現有指令一致
- 成功設定後必須觸發排程重新載入

### REQ-2: UTC Offset Timezone Support
**Priority:** High
**Scenario:** 使用者可以使用 `UTC+8` 格式設定時區

**Acceptance Criteria:**
- 支援 UTC offset 格式: `UTC+8`, `UTC-5`, `UTC+5:30`
- 支援格式變體: `UTC+08:00`, `UTC-0500`
- 將 UTC offset 轉換為對應的固定 offset timezone
- 繼續支援現有的 IANA 時區名稱格式

**Constraints:**
- 必須產生與 APScheduler 相容的 timezone 物件
- UTC offset 必須在合理範圍內 (-12:00 到 +14:00)
- 轉換後的 timezone 必須能正確處理 DST (雖然固定 offset 不受 DST 影響)

### REQ-3: Legacy Command Migration
**Priority:** High
**Scenario:** 移除舊指令,引導使用者使用新的統一指令

**Acceptance Criteria:**
- 移除 `/set_channel`, `/set_role`, `/set_post_time`, `/set_timezone` 指令
- 資料庫中現有的設定資料繼續有效
- 現有的排程不受影響
- 提供清晰的遷移文件

**Constraints:**
- 不可修改資料庫 schema
- 不可破壞現有的驗證邏輯
- 不可影響現有的排程機制
- 必須在 CHANGELOG 和 README 中說明變更

### REQ-4: User Experience Improvements
**Priority:** Medium
**Scenario:** 提供清晰的錯誤訊息和使用指引

**Acceptance Criteria:**
- 當使用者首次設定時未提供 `channel`,顯示清晰的錯誤訊息
- 當時區格式無效時,提供範例說明
- 成功設定後,顯示所有已設定的值
- 更新文件說明新的指令格式

**Constraints:**
- 錯誤訊息必須使用繁體中文
- 必須保持與現有 UI 風格一致

## Success Criteria

### Functional Success
1. 使用者可以使用 `/config channel:#general time:08:00 timezone:UTC+8` 一次完成設定
2. 使用者可以使用 `/config time:09:00` 僅更新時間,不影響其他設定
3. 使用者可以使用 `UTC+8` 或 `Asia/Taipei` 設定時區,兩者都能正常運作
4. 舊的 `/set_*` 指令已被移除,不再出現在指令列表中
5. 資料庫中現有的設定資料在移除舊指令後仍然有效

### Technical Success
1. 所有現有測試通過 (如果有)
2. 新增的時區轉換邏輯通過單元測試
3. 排程系統正確處理 UTC offset 時區
4. 資料庫操作保持原子性和一致性
5. 參數驗證在更新前完成,確保不會出現部分更新的情況

### User Experience Success
1. 使用者反映設定流程更簡便
2. 錯誤訊息清晰易懂
3. 文件更新完整,包含遷移指南
4. CHANGELOG 清楚說明 breaking changes

## Design Decisions

### Decision 1: Command Naming
**Chosen:** `/config`
**Rationale:** 更語義化,清楚表達這是配置指令。使用 `guild_only` 可降低與其他 bot 衝突的風險。

### Decision 2: Legacy Commands
**Chosen:** 移除舊指令
**Rationale:** 簡化維護負擔,避免功能重複。使用者需要遷移到新指令。
**Migration Plan:**
- 在版本更新說明中明確告知變更
- 提供指令對照表
- 考慮在移除前提供過渡期警告

### Decision 3: UTC Offset Storage
**Chosen:** 儲存原始輸入
**Rationale:** 保留使用者意圖,`/show_settings` 顯示時更直觀。讀取時再轉換為 pytz timezone 物件。
**Implementation:** 資料庫中儲存 "UTC+8",使用時透過 `parse_timezone()` 函數轉換。

### Decision 4: Validation Strategy
**Chosen:** 先驗證所有參數,再執行更新
**Rationale:** 確保原子性,避免部分更新成功、部分失敗的情況。
**Implementation:**
1. 收集所有參數
2. 逐一驗證每個參數
3. 如果任一驗證失敗,回傳錯誤,不執行任何更新
4. 所有驗證通過後,一次性更新資料庫

## Dependencies

### Internal Dependencies
- `utils/database.py`: 可能需要新增統一的設定更新方法
- `cogs/slash_commands_cog.py`: 新增 `/config` 指令
- `cogs/schedule_manager_cog.py`: 確保支援 UTC offset timezone

### External Dependencies
- `pytz`: 時區處理
- `discord.py`: 指令參數類型
- `APScheduler`: 排程觸發器

### Risk Mitigation
- **Risk:** UTC offset 轉換錯誤導致排程時間不正確
  - **Mitigation:** 完整的單元測試覆蓋所有 offset 範圍

- **Risk:** 移除舊指令導致現有使用者和自動化腳本失效
  - **Mitigation:**
    - 在 CHANGELOG 中明確標註為 BREAKING CHANGE
    - 在 README 中提供指令對照表和遷移指南
    - 考慮在發布前通知主要使用者

- **Risk:** 資料庫中混合儲存不同格式的時區
  - **Mitigation:**
    - 統一使用 `parse_timezone()` 函數處理所有時區字串
    - 支援讀取舊格式 (IANA) 和新格式 (UTC offset)
    - 不強制轉換現有資料

- **Risk:** 參數驗證失敗時,錯誤訊息不夠清晰
  - **Mitigation:**
    - 為每種驗證失敗情況提供具體的錯誤訊息
    - 在錯誤訊息中提供正確的格式範例

## Implementation Notes

### Timezone Conversion Strategy
```python
def parse_timezone(tz_string: str) -> pytz.tzinfo.BaseTzInfo:
    """
    Parse timezone string supporting both IANA names and UTC offsets.

    Supports:
    - IANA timezone names: "Asia/Taipei", "America/New_York", "UTC"
    - UTC offset formats: "UTC+8", "UTC-5", "UTC+5:30", "UTC+08:00", "UTC-0530"

    Examples:
        - "Asia/Taipei" -> pytz.timezone("Asia/Taipei")
        - "UTC+8" -> pytz.FixedOffset(480)  # 8 * 60 minutes
        - "UTC-5:30" -> pytz.FixedOffset(-330)  # -(5 * 60 + 30) minutes

    Raises:
        ValueError: If timezone string is invalid
    """
    # Try IANA timezone first
    try:
        return pytz.timezone(tz_string)
    except pytz.exceptions.UnknownTimeZoneError:
        pass

    # Try UTC offset format
    import re
    pattern = r'^UTC([+-])(\d{1,2})(?::(\d{2}))?$'
    match = re.match(pattern, tz_string, re.IGNORECASE)

    if match:
        sign = 1 if match.group(1) == '+' else -1
        hours = int(match.group(2))
        minutes = int(match.group(3)) if match.group(3) else 0

        # Validate range
        if not (-12 <= hours <= 14 and 0 <= minutes < 60):
            raise ValueError(f"UTC offset out of range: {tz_string}")

        total_minutes = sign * (hours * 60 + minutes)

        # Return a timezone-like object compatible with APScheduler
        from datetime import timezone, timedelta
        return timezone(timedelta(minutes=total_minutes))

    raise ValueError(f"Invalid timezone format: {tz_string}")
```

### Unified Config Command Structure
```python
@app_commands.command(name="config", description="設定 LeetCode 每日挑戰的所有配置")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="發送每日挑戰的頻道",
    role="要標記的身分組 (可選)",
    time="發送時間,格式 HH:MM (可選)",
    timezone="時區,支援 Asia/Taipei 或 UTC+8 格式 (可選)"
)
async def config_command(
    self,
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    role: Optional[discord.Role] = None,
    time: Optional[str] = None,
    timezone: Optional[str] = None
):
    """Unified configuration command for LeetCode daily challenge"""
    server_id = interaction.guild.id

    # Step 1: Validate all parameters before any database operation
    validated_params = {}

    # Validate channel (required for first-time setup)
    settings = self.bot.db.get_server_settings(server_id)
    if not settings and not channel:
        await interaction.response.send_message(
            "首次設定時必須指定 channel 參數。\n"
            "範例: `/config channel:#general time:08:00 timezone:UTC+8`",
            ephemeral=True
        )
        return

    if channel:
        validated_params['channel_id'] = channel.id

    # Validate role
    if role:
        validated_params['role_id'] = role.id

    # Validate time format
    if time:
        try:
            hour, minute = map(int, time.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
            validated_params['post_time'] = time
        except ValueError:
            await interaction.response.send_message(
                "時間格式錯誤,請使用 HH:MM 格式 (例如 08:00 或 23:59)。",
                ephemeral=True
            )
            return

    # Validate timezone
    if timezone:
        try:
            parse_timezone(timezone)  # Validate but don't store the object
            validated_params['timezone'] = timezone  # Store original string
        except ValueError as e:
            await interaction.response.send_message(
                f"無效的時區格式: {e}\n"
                f"支援格式:\n"
                f"- IANA 時區名稱: Asia/Taipei, America/New_York, UTC\n"
                f"- UTC offset: UTC+8, UTC-5, UTC+5:30",
                ephemeral=True
            )
            return

    # Step 2: All validations passed, perform database update
    if not validated_params:
        await interaction.response.send_message(
            "請至少提供一個要更新的參數。",
            ephemeral=True
        )
        return

    # Merge with existing settings
    if settings:
        final_params = {
            'channel_id': validated_params.get('channel_id', settings['channel_id']),
            'role_id': validated_params.get('role_id', settings.get('role_id')),
            'post_time': validated_params.get('post_time', settings.get('post_time', '00:00')),
            'timezone': validated_params.get('timezone', settings.get('timezone', 'UTC'))
        }
    else:
        final_params = {
            'channel_id': validated_params['channel_id'],
            'role_id': validated_params.get('role_id'),
            'post_time': validated_params.get('post_time', '00:00'),
            'timezone': validated_params.get('timezone', 'UTC')
        }

    success = self.bot.db.set_server_settings(
        server_id,
        final_params['channel_id'],
        final_params['role_id'],
        final_params['post_time'],
        final_params['timezone']
    )

    if success:
        # Build success message
        channel_obj = self.bot.get_channel(final_params['channel_id'])
        channel_mention = channel_obj.mention if channel_obj else f"ID: {final_params['channel_id']}"

        role_mention = "未設定"
        if final_params['role_id']:
            role_obj = interaction.guild.get_role(final_params['role_id'])
            role_mention = role_obj.mention if role_obj else f"ID: {final_params['role_id']}"

        await interaction.response.send_message(
            f"✅ 設定已更新:\n"
            f"- 頻道: {channel_mention}\n"
            f"- 身分組: {role_mention}\n"
            f"- 時間: {final_params['post_time']}\n"
            f"- 時區: {final_params['timezone']}",
            ephemeral=True
        )

        # Reschedule
        await self._reschedule_if_available(server_id, "config")
    else:
        await interaction.response.send_message(
            "設定時發生錯誤,請稍後再試。",
            ephemeral=True
        )
```

### Migration Guide Template
```markdown
# Migration Guide: v1.x to v2.0

## Breaking Changes

### Unified Configuration Command

舊的設定指令已被移除,請使用新的 `/config` 指令:

| 舊指令 | 新指令 |
|--------|--------|
| `/set_channel #general` | `/config channel:#general` |
| `/set_role @role` | `/config role:@role` |
| `/set_post_time 08:00` | `/config time:08:00` |
| `/set_timezone Asia/Taipei` | `/config timezone:Asia/Taipei` |

### 一次設定多個參數

新指令支援一次設定多個參數:

```
/config channel:#general time:08:00 timezone:UTC+8 role:@LeetCode
```

### UTC Offset 支援

現在支援 UTC offset 格式的時區:

```
/config timezone:UTC+8
/config timezone:UTC-5
/config timezone:UTC+5:30
```

## 資料遷移

不需要手動遷移資料,現有的設定會自動保留。
```

