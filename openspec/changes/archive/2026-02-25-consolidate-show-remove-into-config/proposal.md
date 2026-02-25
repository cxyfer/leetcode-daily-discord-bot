# Proposal: Consolidate /show_settings and /remove_channel into /config

## Context

### User Need
先前的 `2026-02-25-unified-config-command` 變更已將 `/set_channel`、`/set_role`、`/set_post_time`、`/set_timezone` 整合為 `/config` 命令，並標記舊指令為 deprecated。現在需要進一步將 `/show_settings` 和 `/remove_channel` 也整合進 `/config`，繼續減少頂層命令數量。

### Current Implementation Constraints

**C1: `/show_settings` 行為** (cogs/slash_commands_cog.py:659-688)
- 不需要 `manage_guild` 權限，任何人都可查看
- 讀取 `get_server_settings()`，組裝 embed 顯示 channel/role/time/timezone
- 若無設定則提示用 `/config channel:<頻道>` 開始設定
- 呼叫 `create_settings_embed()` (utils/ui_helpers.py:502-516) 產生 embed

**C2: `/remove_channel` 行為** (cogs/slash_commands_cog.py:791-829)
- 需要 `manage_guild` 權限
- 呼叫 `delete_server_settings()` 刪除整個 server 的設定記錄
- 成功後觸發 `_reschedule_if_available()` 取消排程
- 有 error handler 處理 `MissingPermissions` 和 `NoPrivateMessage`

**C3: 現有 `/config` 命令** (cogs/slash_commands_cog.py:524-658)
- 需要 `manage_guild` 權限
- 接受 `channel`, `role`, `time`, `timezone`, `clear_role` 參數
- 若無任何參數則回傳「請至少提供一個要更新的參數」
- 成功後顯示所有當前設定值

**C4: Discord `app_commands` 限制**
- 無法用 subcommand group 與 optional parameter 混用（Discord API 限制：command 有 subcommand 後就不能有頂層參數）
- 選項：(a) 保持現有可選參數設計 + 新增語義參數，或 (b) 轉為 subcommand group 但失去一次設定多項的便利性

**C5: 權限不對稱**
- `/show_settings` 無需 `manage_guild`，但 `/config` 整體需要 `manage_guild`
- 若 `show` 整合進 `/config`，需要決定：降低整個 `/config` 的權限門檻（不合理），還是接受 `show` 也需要 `manage_guild`（行為變更）

**C6: Database 層** (utils/database.py:235-255)
- `delete_server_settings()` 已存在，直接刪除整行記錄
- `/config` 目前的 `clear_role` 只清除 role_id 欄位，不刪除整行

## Requirements

### REQ-1: Integrate "show" into /config (無參數行為)
**Priority:** High

**Acceptance Criteria:**
- 當 `/config` 不帶任何參數時，顯示當前伺服器設定（等同現有 `/show_settings` 行為）
- 使用相同的 `create_settings_embed()` 產生 embed
- 若無設定記錄，提示用 `/config channel:<頻道>` 開始設定

**Constraints:**
- 權限提升為 `manage_guild`（與 `/config` 一致），這是可接受的取捨——檢視設定是管理員行為
- 移除現行「請至少提供一個要更新的參數」邏輯，改為顯示設定

### REQ-2: Integrate "reset" into /config
**Priority:** High

**Acceptance Criteria:**
- 新增 `reset: bool = False` 參數到 `/config`
- 當 `reset=True` 時，刪除整個伺服器設定並取消排程
- `reset` 與其他設定參數互斥（不可同時帶 channel/role/time/timezone/clear_role）

**Constraints:**
- 呼叫現有的 `delete_server_settings()` 方法
- 成功後觸發 `_reschedule_if_available()` 取消排程
- 若無設定記錄，提示無需重置

### REQ-3: Legacy Command Removal
**Priority:** High

**Acceptance Criteria:**
- 移除 `/show_settings` 命令及其方法
- 移除 `/remove_channel` 命令、其方法及 error handler
- 移除已標記 deprecated 的 `/set_channel`、`/set_role`、`/set_post_time`、`/set_timezone` 命令及其 error handlers
- 移除 database layer 中僅被舊命令使用的 `set_channel()`、`set_role()`、`set_post_time()`、`set_timezone()` wrapper 方法
- 清理不再需要的 imports（`pytz` 在 cog 中若不再直接使用則移除）

**Constraints:**
- `set_server_settings()`、`get_server_settings()`、`delete_server_settings()`、`get_all_servers()` 必須保留（被 `/config` 和 scheduler 使用）
- `DEFAULT_POST_TIME` / `DEFAULT_TIMEZONE` 常數可能不再需要（確認後移除）

## Success Criteria

### Functional
1. `/config`（無參數）顯示當前設定 embed
2. `/config reset:True` 刪除設定並停止排程
3. `/config channel:#ch time:08:00` 等設定功能不受影響
4. 頂層命令列表中不再出現 `/show_settings`、`/remove_channel`、`/set_*` 命令
5. 排程系統正常運作

### Technical
1. `slash_commands_cog.py` 中僅保留 `/daily`、`/daily_cn`、`/problem`、`/recent`、`/config` 五個命令
2. `database.py` 中 `SettingsDatabaseManager` 僅保留 `get_server_settings`、`set_server_settings`、`get_all_servers`、`delete_server_settings` 四個公開方法

## Design Decisions

### D1: Show 的整合方式 — 無參數時顯示
**Rationale:** 避免 Discord subcommand 限制，保持 `/config` 一次設定多項的便利性。無參數 = 查看設定，有參數 = 更新設定，語義清晰。

### D2: Remove 的命名 — `reset` 而非 `remove_channel`
**Rationale:** 實際行為是重置整個伺服器設定（不只是 channel），`reset` 更準確反映語義。

### D3: 權限統一 — show 也需要 manage_guild
**Rationale:** `/config` 是管理員命令，show 行為整合後繼承其權限。這是可接受的取捨，伺服器設定不是敏感資訊但管理員查看更合理。

### D4: 完全移除舊命令 — 不再保留過渡期
**Rationale:** 先前版本已加入 deprecated 警告，現在進行最終移除。

## Dependencies

### Internal
- `cogs/slash_commands_cog.py`: 主要修改目標
- `utils/database.py`: 清理 wrapper 方法
- `utils/ui_helpers.py`: `create_settings_embed()` 不需修改，繼續使用

### Risks
- **R1: show 權限提升** → 原本任何人可查看設定，現在需要 manage_guild。可能影響少數非管理員使用者。Mitigation: 設定資訊本來就是管理層面的，影響面小。
- **R2: Bot 需要 re-sync 命令** → 移除命令後 Discord 需要重新同步 slash commands。Mitigation: Bot 啟動時自動同步。
