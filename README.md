<div align="center">

# 🎯 LeetCode Daily Challenge Discord Bot

*A modern Discord bot that fetches and shares LeetCode daily challenges automatically.*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&logo=python)](https://www.python.org)
[![Discord](https://img.shields.io/badge/Discord-bot-5865F2.svg?style=flat-square&logo=discord)](https://discord.com/developers/docs/intro)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

## ✨ Features

- 🔄 **Automatic Daily Challenges**: Schedule `leetcode.com`, `sheep`, and `0x3f` problem sets
- ⏰ **Independent Scheduled Delivery**: Configure up to three independent daily pushes per server, each with its own channel, role, time, and timezone
- 🎮 **Slash Commands**: Simple slash-command interface for daily problems, lookup, recent submissions, and settings
- 🌐 **Multi-server Support**: Each Discord server keeps its own configuration
- 🔔 **Custom Notifications**: Configure the target channel and optional role mention
- 📅 **Historical Challenges**: View past daily challenges by date
- 🔍 **Problem Lookup**: Query one or multiple problems from supported sources
- 📈 **Submission Tracking**: View recent accepted submissions for a LeetCode user
- 🤖 **AI-Powered Features**: Optional translation and inspiration via Gemini
- 🧭 **Similar Problem Search**: Search related problems through the configured remote API backend
- 💾 **Caching**: Cache problem data and AI results to reduce repeated requests

## 🚀 Quick Start

### 1. Create your Discord bot (if you do not already have one)

<details>
<summary>Show Discord Developer Portal setup steps</summary>

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a **New Application**.
3. Open **Overview → Bot**.
4. Set the bot icon, banner, and username. Use **Reset Token** to generate or reset the bot token, then paste it into `discord.token` in `config.toml`. Also enable:
   - **Message Content Intent**
5. Open **Overview → Installation**.
6. Enable **Guild Install** (required) and **User Install** if needed.
7. Under **Guild Install**, configure:
   - Scopes: `applications.commands`, `bot`
   - Permissions: `Embed Links`, `Send Messages`, `Use Slash Commands`
8. Copy the **Install Link** from that page and use it to install the app in your Discord server.

</details>

### 2. Clone the repository

```bash
git clone https://github.com/cxyfer/leetcode-daily-discord-bot.git
cd leetcode-daily-discord-bot
```

### 3. Configure the bot

```bash
cp config.toml.example config.toml
```

Then edit `config.toml` and set at least:

- `discord.token`
- `api.base_url` if you use a custom API backend
- `llm.gemini.api_key` if you want AI-powered features

### 4. Run the bot

```bash
uv run bot.py
```

### 5. Optional legacy database cleanup

<details>
<summary>Show legacy database cleanup steps</summary>

Use this only when upgrading an older `data/data.db` that still contains legacy tables such as `vec_embeddings` or `vec0`.
Fresh installs do not need this step.

```bash
# Stop the bot or container before cleanup.
uv run python data/cleanup_runtime_db.py

# Optional: target a different database or skip VACUUM.
uv run python data/cleanup_runtime_db.py --db-path /path/to/data.db --skip-vacuum
```

The helper creates a timestamped backup, rebuilds the runtime schema from `data/init_db_schema.sql`, migrates `server_settings`, `llm_translate_results`, and `llm_inspire_results` when present, and runs `VACUUM` unless you pass `--skip-vacuum`.

The bot also migrates the former single-push `server_settings` schema automatically at startup. Before changing the schema it creates a timestamped `.pre-push-redesign.bak` SQLite backup, then each legacy schedule is migrated to the `leetcode.com` source. The backup is retained for operator rollback and is never read by the normal runtime path.

If you need to initialize an empty database manually:

```bash
sqlite3 data/data.db < data/init_db_schema.sql
```

</details>

## 🐳 Docker Image

Official GHCR image: `ghcr.io/cxyfer/leetcode-daily-discord-bot`

```bash
docker run -d --name leetcode-daily-discord-bot \
  --restart unless-stopped \
  -v /path/to/config.toml:/app/config.toml:ro \
  -v /path/to/data:/app/data \
  -v /path/to/logs:/app/logs \
  ghcr.io/cxyfer/leetcode-daily-discord-bot:latest
```

## 🛠️ Configuration

> [!IMPORTANT]
> Starting from **v2.0**, this project uses [cxyfer/oj-api-rs](https://github.com/cxyfer/oj-api-rs) as the external problem provider backend for problem retrieval, identifier resolution, and similar-problem search.
> 
> The hosted service at `oj-api.gdst.dev` is the default backend, but you can point `api.base_url` to your own deployment if needed.

> [!WARNING]
> Starting from **v2.0**, `config.toml` is the only supported and documented configuration format. Legacy `.env` fallback may still exist in some runtime paths for backward compatibility, but its support is no longer guaranteed.

Example configuration:

```toml
[discord]
token = "your_discord_bot_token_here"

[llm.gemini]
api_key = "your_google_gemini_api_key_here"  # Optional

[api]
base_url = "https://oj-api.gdst.dev/api/v1"  # Remote API backend
# token = "your_api_token_here"                # Optional Bearer token
timeout = 10

[schedule]
post_time = "00:00"
timezone = "UTC"
```

See `config.toml.example` for all available options.

## 📝 Usage

### Slash Commands

| Command | Description | Required Permissions |
|---------|-------------|---------------------|
| `/daily [date] [public]` | Display the LeetCode.com daily challenge<br>• Optional: `YYYY-MM-DD` for historical challenges<br>• Optional: `public` to show the response publicly<br>• Historical data is available from April 2020 onwards | None |
| `/daily_cn [date] [public]` | Display the LeetCode.cn daily challenge<br>• Optional: `YYYY-MM-DD` for historical challenges<br>• Optional: `public` to show the response publicly | None |
| `/problem <problem_ids> [source] [domain] [public] [message] [title]` | Query one or multiple problems<br>• `problem_ids`: Single ID or comma-separated IDs<br>• Supports `source:id` format such as `atcoder:abc001_a` or `leetcode:1`<br>• `source`: Problem source filter or hint<br>• `domain`: `com` or `cn` for LeetCode (default: `com`)<br>• `public`: Show the response publicly<br>• `message`: Optional personal note (max 500 chars)<br>• `title`: Custom title for multi-problem mode (max 100 chars)<br>• Supports up to 20 problems per query | None |
| `/recent <username> [limit] [public]` | View recent accepted submissions for a user<br>• `username`: LeetCode username (LCUS only)<br>• `limit`: Number of submissions (1-50, default: 20)<br>• `public`: Show the response publicly | None |
| `/similar [query] [problem] [top_k] [source] [public]` | Find similar problems through the configured remote API backend<br>• `query`: Free-text query (optional when `problem` is provided)<br>• `problem`: Existing problem ID or URL<br>• `top_k`: Number of results (default: 5, capped at 20)<br>• `source`: Problem source filter<br>• `public`: Show the response publicly | None |
| `/config [source] [channel] [role] [time] [timezone] [clear_role] [language] [remove] [reset]` | View or update daily-push settings<br>• No parameters: Show the shared language and all configured pushes<br>• `source`: `leetcode.com`, `sheep`, or `0x3f`; push updates default to `leetcode.com` when omitted<br>• `channel`, `role`, `time`, `timezone`, and `clear_role`: Update only the selected source<br>• `language`: Shared by every push in the server<br>• `remove`: Remove only the explicitly selected source after confirmation<br>• `reset`: Reset the language and all pushes after confirmation | Manage Guild |

### Server setup for daily notifications

1. Run `/config channel:<channel>` to create the default `leetcode.com` push.
2. Add optional independent pushes with `/config source:sheep channel:<channel>` and `/config source:0x3f channel:<channel>`.
3. Set `role`, `time`, and `timezone` independently by including the target `source`; each server can have at most one push per source.
4. Use `/config` with no arguments to review the shared language and all pushes.
5. Use `/config source:<source> remove:true` to remove one push, or `/config reset:true` to remove every server setting.

### Multi-Problem Features

The `/problem` command supports querying multiple problems at once.

#### Overview Mode

When querying multiple problems, the bot displays:

- **Grouped Display**: Problems are grouped for easier reading
- **Problem Links**: Direct links to supported problem pages
- **Difficulty Indicators**: Source-aware difficulty colors or emojis when available
- **Problem Stats**: Rating and acceptance rate when available
- **Interactive Buttons**: Numbered buttons for detailed problem views

#### Customization Options

- **Custom Title**: Replace the default title with your own (max 100 characters)
- **Personal Message**: Add notes, study plans, or context (max 500 characters)
- **User Attribution**: Shows your name and avatar when title or message is provided

### Command Examples

<details>
<summary>Daily Challenge Commands</summary>

```text
/daily
/daily public:true
/daily date:2024-01-15
```

</details>

<details>
<summary>Problem Lookup</summary>

```text
# Single problem lookup
/problem problem_ids:1
/problem problem_ids:1 public:true

# Multiple problems lookup
/problem problem_ids:1,2,3
/problem problem_ids:1,2,3 title:Dynamic Programming Practice
/problem problem_ids:1,2,3 message:Today's study plan
/problem problem_ids:1,2,3 title:Weekly Contest Problems message:Need to practice these

# AtCoder problems
/problem problem_ids:abc001_a
/problem problem_ids:atcoder:abc001_a
/problem problem_ids:abc001_a source:atcoder

# Mixed sources
/problem problem_ids:1,abc001_a,leetcode:15
```

</details>

<details>
<summary>Recent Submissions</summary>

```text
/recent username:alice
/recent username:alice limit:50
/recent username:alice limit:50 public:true
```

</details>

<details>
<summary>Similar Problem Search</summary>

```text
/similar query:"array sorting"
/similar query:"two pointers" top_k:3
/similar query:"dp with knapsack" public:true
/similar problem:1
/similar problem:atcoder:abc100_a source:atcoder
```

</details>

<details>
<summary>Server Configuration</summary>

```text
/config
/config channel:#general
/config channel:#general time:08:00 timezone:UTC+8
/config source:sheep channel:#sheep-daily time:09:00 timezone:Asia/Taipei
/config source:0x3f channel:#daily-problems role:@DailyChallenge
/config source:sheep clear_role:true
/config language:en-US
/config source:0x3f remove:true
/config reset:true
```

</details>

## 🗞️ Release Notes

See [CHANGELOG.md](CHANGELOG.md) for versioned release notes and history.

## 🛠️ Development

### Setup Development Environment

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
uv sync --extra dev
```

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
```

### Running Tests

```bash
uv run pytest
uv run pytest tests/test_similar_cog.py
```

## 🤝 Contributing

Contributions are welcome. Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss the proposal.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
