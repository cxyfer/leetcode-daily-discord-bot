<div align="center">

# 🎯 LeetCode Daily Challenge Discord Bot

*A modern Discord bot that automatically fetches and shares LeetCode daily challenges*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square&logo=python)](https://www.python.org)
[![Discord](https://img.shields.io/badge/Discord-bot-5865F2.svg?style=flat-square&logo=discord)](https://discord.com/developers/docs/intro)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

## ✨ Features

- 🔄 **Automatic Daily Challenge**: Automatically retrieves and posts LeetCode daily challenges
- ⏰ **Scheduled Delivery**: Configurable posting time for each server
- 🎮 **Slash Commands**: Easy-to-use slash commands for manual control
- 📊 **Rich Information**: Includes title, difficulty, link, tags, and more
- 🌐 **Multi-server Support**: Independent settings for each Discord server
- 🔔 **Custom Notifications**: Configurable role mentions and channels
- 🌍 **Timezone Support**: Server-specific timezone settings
- 📅 **Historical Challenges**: View past daily challenges by date
- 🔍 **Problem Lookup**: Query single or multiple LeetCode problems with custom titles and messages
- 📈 **Submission Tracking**: View recent accepted submissions for any user
- 🤖 **AI-Powered Features**: Optional problem translation and inspiration (requires Gemini API key)
- 🧭 **Similar Problem Search**: Find related problems through the configured remote API backend
- 💾 **Smart Caching**: Efficient caching system for better performance

## 🚀 Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/cxyfer/leetcode-daily-discord-bot.git
   cd leetcode-daily-discord-bot
   ```

2. Configure your bot:
   ```bash
   # Copy and edit the configuration file
   cp config.toml.example config.toml
   # Edit config.toml with your settings
   
   # Alternative: Use environment variables (.env)
   cp .env.example .env
   # Edit .env with your Discord bot token
   ```

3. Optional database maintenance:
   ```bash
   # Fresh installs do not need any legacy migration step.

   # If you are upgrading an existing data/data.db and want to remove
   # legacy runtime tables, run this manually while the bot is stopped.
   sqlite3 data/data.db < data/cleanup_db_schema.sql

   # If you need to initialize an empty database file manually,
   # apply the current runtime schema yourself.
   sqlite3 data/data.db < data/init_db_schema.sql
   ```

   These SQL files are operator-facing maintenance assets. The bot runtime does not execute cleanup or init SQL automatically.

4. Run the bot:
   ```bash
   uv run bot.py
   ```

   The repository-root `bot.py` is the supported launcher. It adds `src/` to the import path and delegates startup to the packaged runtime under `src/bot/`.

## 🐳 Docker Image

Official GHCR image: `ghcr.io/cxyfer/leetcode-daily-discord-bot`  
If you are using a fork, replace it with `ghcr.io/<your-owner>/<your-repo>`.

### Docker Run (config.toml)

```bash
mkdir -p data logs
docker run -d --name leetcode-daily-discord-bot \
  --restart unless-stopped \
  -v /path/to/config.toml:/app/config.toml:ro \
  -v /path/to/data:/app/data \
  -v /path/to/logs:/app/logs \
  ghcr.io/cxyfer/leetcode-daily-discord-bot:latest
```

### Docker Run (.env)

```bash
mkdir -p data logs
docker run -d --name leetcode-daily-discord-bot \
  --restart unless-stopped \
  -v /path/to/.env:/app/.env:ro \
  -v /path/to/data:/app/data \
  -v /path/to/logs:/app/logs \
  ghcr.io/cxyfer/leetcode-daily-discord-bot:latest
```

- The container starts through `python /app/bot.py`, which delegates into the packaged runtime under `src/bot/`.
- `/app/data` contains `data.db`; keep it mapped to persist settings and cache.
- `config.toml` is recommended; `.env` is for backward compatibility.
- Use `:v1.0.0` to pin a specific release; `:latest` tracks the newest image.

## 🛠️ Configuration

### Configuration Methods

The bot supports two configuration methods:

#### 1. TOML Configuration (Recommended)

Create a `config.toml` file from the example:

```toml
[discord]
token = "your_discord_bot_token_here"

[llm.gemini]
api_key = "your_google_gemini_api_key_here"  # Optional, for AI features

[schedule]
post_time = "00:00"  # Default posting time
timezone = "UTC"     # Default timezone
```

See `config.toml.example` for all available options.

#### 2. Environment Variables

For backward compatibility, you can use a `.env` file:

```bash
DISCORD_TOKEN=your_bot_token_here
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here  # Optional
GOOGLE_API_KEY=your_gemini_api_key_here         # Optional alternative
GEMINI_API_KEY=your_gemini_api_key_here         # Optional alternative
POST_TIME=00:00  # Optional
TIMEZONE=UTC     # Optional
```

**Note**: Environment variables take precedence over `config.toml` settings.

### Required Bot Permissions
- `Send Messages`
- `Embed Links`
- `Use Slash Commands`

### Required Intents
- `Message Content` - Receive message content
  - Note: When the bot joins more than 100 servers, this permission needs to be verified and approved by Discord

## 📝 Usage

### Slash Commands

| Command | Description | Required Permissions |
|---------|-------------|---------------------|
| `/daily [date] [public]` | Display LeetCode.com (LCUS) daily challenge<br>• Optional: YYYY-MM-DD for historical challenges<br>• Optional: `public` - Show response publicly (default: private)<br>• Note: Historical data available from April 2020 onwards | None |
| `/daily_cn [date] [public]` | Display LeetCode.cn (LCCN) daily challenge<br>• Optional: YYYY-MM-DD for historical challenges<br>• Optional: `public` - Show response publicly (default: private) | None |
| `/problem <problem_ids> [source] [domain] [public] [message] [title]` | Query one or multiple problems<br>• `problem_ids`: Single ID (e.g., `1`) or comma-separated IDs (e.g., `1,2,3`)<br>• Supports `source:id` format (e.g., `atcoder:abc001_a`, `leetcode:1`)<br>• `source`: Problem source - `leetcode` (default) or `atcoder`<br>• `domain`: LeetCode domain - `com` or `cn` (default: `com`)<br>• `public`: Show response publicly (default: private)<br>• `message`: Optional personal message/note (max 500 chars)<br>• `title`: Custom title for multi-problem mode (max 100 chars)<br>• Note: Supports up to 10 problems per query | None |
| `/recent <username> [limit] [public]` | View recent accepted submissions for a user<br>• `username`: LeetCode username (LCUS only)<br>• `limit`: Number of submissions (1-50, default: 20)<br>• `public`: Show response publicly (default: private) | None |
| `/similar <query> [top_k] [source] [public]` | Find similar problems through the configured remote API backend<br>• `query`: Problem description or keywords<br>• `top_k`: Number of results (default: 5)<br>• `source`: Problem source (default: leetcode)<br>• `public`: Show response publicly (default: private) | None |
| `/set_channel` | Set notification channel for daily challenges | Manage Channels |
| `/set_role` | Set role to mention with daily challenges | Manage Roles |
| `/set_post_time` | Set posting time (HH:MM format) | Manage Guild |
| `/set_timezone` | Set server timezone for scheduling | Manage Guild |
| `/show_settings` | Display current server settings | None |
| `/remove_channel` | Remove channel settings | Manage Channels |

### Command Examples

#### Daily Challenge Commands
```
/daily                    # Get today's LeetCode.com challenge (private)
/daily public:true        # Get today's challenge and show response publicly
/daily date:2024-01-15    # Get historical challenge from Jan 15, 2024
```

#### Problem Lookup
```
# Single problem lookup
/problem problem_ids:1                    # Get Two Sum problem from LeetCode.com (private)
/problem problem_ids:1 public:true        # Get Two Sum problem publicly

# Multiple problems lookup
/problem problem_ids:1,2,3                # Get multiple problems with overview
/problem problem_ids:1,2,3 title:Dynamic Programming Practice  # Custom title
/problem problem_ids:1,2,3 message:Today's study plan         # With personal note
/problem problem_ids:1,2,3 title:Weekly Contest Problems message:Need to practice these  # Both title and message

# Multi-problem with domain selection
/problem problem_ids:1,2,3 domain:cn      # Query from LeetCode.cn

# AtCoder problems (auto-detected or explicit source)
/problem problem_ids:abc001_a             # Auto-detect AtCoder from ID pattern
/problem problem_ids:atcoder:abc001_a     # Explicit source:id format
/problem problem_ids:abc001_a source:atcoder  # Explicit source parameter

# Mixed sources
/problem problem_ids:1,abc001_a,leetcode:15   # Mix LeetCode and AtCoder
```

#### Recent Submissions
```
/recent username:alice              # View 20 recent submissions (private)
/recent username:alice limit:50     # View 50 recent submissions
/recent username:alice limit:50 public:true  # View 50 submissions publicly
```

#### Similar Problem Search
```
/similar query:"array sorting"                # Find related problems (private)
/similar query:"two pointers" top_k:3         # Limit results to 3
/similar query:"dp with knapsack" public:true # Show results publicly
```

> Note: `/similar` is remote API-backed. No local embedding build or index maintenance step is required in this repository.

#### Server Configuration
```
/set_channel              # Set current channel for daily notifications
/set_role                 # Configure role to ping
/set_post_time time:08:00 # Set daily post time to 8:00 AM
/set_timezone timezone:America/New_York  # Set timezone
/show_settings            # View current configuration
```

### Server Configuration Steps

1. Set up notification channel using `/set_channel` (Required)
2. Configure role mentions with `/set_role` (Optional)
3. Set posting time and timezone (Optional)
4. Verify settings with `/show_settings`

### Runtime Layout

- `bot.py` is the only supported repository-root runtime entrypoint.
- The packaged application code lives under `src/bot/`.
- `/similar` is implemented by `bot.api_client` and `bot.cogs.similar_cog` and uses the configured remote API backend.
- This repository no longer provides a local similarity maintenance CLI, a local embeddings package, or other repository-root tools for similarity indexing.

### Multi-Problem Features

The `/problem` command supports querying multiple problems at once with enhanced customization:

#### Overview Mode
When querying multiple problems, the bot displays:
- **Grouped Display**: Problems organized in groups of 5 per field
- **Problem Links**: Direct clickable links to LeetCode problems
- **Difficulty Indicators**: Color-coded emojis (🟢 Easy, 🟡 Medium, 🔴 Hard)
- **Problem Stats**: Rating and acceptance rate when available
- **Interactive Buttons**: Click numbered buttons to view detailed problem information

#### Customization Options
- **Custom Title**: Replace the default title with your own (max 100 characters)
- **Personal Message**: Add notes, study plans, or context (max 500 characters)
- **User Attribution**: Shows your name and avatar when title or message is provided

#### Example Use Cases
```
# Study plan organization
/problem problem_ids:70,322,518 title:📚 Dynamic Programming Week 1 message:Focus on bottom-up approach

# Contest preparation
/problem problem_ids:1,15,42 title:🏆 Weekly Contest #420 Prep message:Practice these before Sunday

# Topic-based practice
/problem problem_ids:104,226,543 title:🌳 Binary Tree Fundamentals message:Master tree traversal first
```

## 🗺️ Development Roadmap

- [x] 🎮 **Enhanced Command Interface**
  - [x] Add slash command prompts
  - [x] Reply in the same channel where slash commands are used
  - [x] Add `/problem` command for querying problems by ID
  - [x] Enhanced `/problem` command with multi-problem support and customization
  - [x] Add `/recent` command for viewing user submissions
  - [x] Support historical daily challenges with date parameter
- [x] ⚙️ **Advanced Configuration System**
  - [x] Allow admin users to set the configuration
    - [x] Set the channel to post the daily challenge
    - [x] Set the posting time and timezone
    - [x] Set the role to mention
    - [ ] Set customizable message templates
    - [ ] Integrate the existing excessive setup instructions
    - [ ] More flexible notification settings
- [x] 🌐 **Multi-server Infrastructure**
  - [x] Support server-specific configurations
- [x] 📝 **Code Optimization**
  - [x] Implement improved runtime logging
  - [ ] Implement modular architecture
  - [x] Add comprehensive documentation
- [x] 🇨🇳 **LeetCode.cn Integration**
  - [x] Add slash command `/daily_cn` for LeetCode.cn daily challenge
  - [ ] Implement separate scheduler for LeetCode.cn challenges
- [ ] 🗄️ **Database Integration**
  - [x] Store and query problem information in database
  - [x] Enable historical daily challenge lookup
- [x] 🔍 **Large Language Model Integration**
  - [x] Integrate LLM to generate problem translation and inspiration
  - [x] Cache LLM results to improve performance
- [x] 📊 **User Engagement Features**
  - [x] Track submission records of specific users
  - [x] Interactive navigation for viewing multiple submissions
  - [x] Paginated display with clean UI
  - [ ] Allow users to configure tracked LeetCode accounts
  - [ ] Implement server-wide submission leaderboards
- [ ] 🐳 **Containerization Support**
  - [ ] Add Docker compose file and image
- [ ] 🌍 **Internationalization**
  - [ ] Support multiple display languages

## 🗞️ Release Notes

See [CHANGELOG.md](CHANGELOG.md) for versioned release notes and history.

## 🛠️ Development

### Setup Development Environment

This project uses [uv](https://github.com/astral-sh/uv) for dependency management. To set up the development environment with all dev tools:

```bash
uv sync --extra dev
```

### Code Quality and Testing

We use `ruff` for linting and formatting, and `pytest` for testing.

#### Linting and Formatting
```bash
# Check for linting issues
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Format code
uv run ruff format .
```

#### Running Tests
```bash
# Run all tests with coverage report
uv run pytest

# Run specific test file
uv run pytest tests/test_source_detector.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📦 Dependencies

- [discord.py](https://pypi.org/project/discord.py/) - Discord bot framework
- [tomli](https://pypi.org/project/tomli/) - TOML parsing for Python < 3.11
- [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment variable management
- [requests](https://pypi.org/project/requests/) - HTTP library for API calls
- [pytz](https://pypi.org/project/pytz/) - Timezone handling
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) - HTML parsing
- [colorlog](https://pypi.org/project/colorlog/) - Colored logging output
- [google-genai](https://pypi.org/project/google-genai/) - Google Gemini SDK
- [aiohttp](https://pypi.org/project/aiohttp/) - Asynchronous HTTP client/server

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
