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

3. Run the bot:
   ```bash
   uv run bot.py
   ```

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
| `/daily` | Display today's LeetCode.com (LCUS) daily challenge | None |
| `/daily_cn` | Display today's LeetCode.cn (LCCN) daily challenge | None |
| `/set_channel` | Set notification channel | Manage Channels |
| `/set_role` | Set role to mention | Manage Roles |
| `/set_post_time` | Set posting time (HH:MM) | Manage Guild |
| `/set_timezone` | Set server timezone | Manage Guild |
| `/show_settings` | Display current settings | None |
| `/remove_channel` | Remove channel settings | Manage Channels |

### Server Configuration Steps

1. Set up notification channel using `/set_channel` (Required)
2. Configure role mentions with `/set_role` (Optional)
3. Set posting time and timezone (Optional)
4. Verify settings with `/show_settings`

## 🗺️ Development Roadmap

- [x] 🎮 **Enhanced Command Interface**
  - [x] Add slash command prompts
  - [x] Reply in the same channel where slash commands are used
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
- [ ] 📊 **User Engagement Features**
  - [x] Track submission records of specific users
  - [ ] Allow users to configure tracked LeetCode accounts
  - [ ] Implement server-wide submission leaderboards
- [ ] 🐳 **Containerization Support**
  - [ ] Add Docker compose file and image
- [ ] 🌍 **Internationalization**
  - [ ] Support multiple display languages

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
- [langchain](https://pypi.org/project/langchain/) - LLM application framework
- [langchain-google-genai](https://pypi.org/project/langchain-google-genai/) - Google Gemini LLM integration
- [aiohttp](https://pypi.org/project/aiohttp/) - Asynchronous HTTP client/server

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.