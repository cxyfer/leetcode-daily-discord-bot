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

2. Configure your environment:
   ```bash
   # Copy and edit the environment file
   mv .env.example .env
   # Edit .env with your Discord bot token
   ```

3. Run the bot:
   ```bash
   uv run discord_bot.py
   ```

## 🛠️ Configuration

### Required Bot Permissions
- `Send Messages`
- `Embed Links`
- `Use Slash Commands`

### Required Intents
- `Message Content` - Receive message content
  - Note: When the bot joins more than 100 servers, this permission needs to be verified and approved by Discord

### Environment Variables
```bash
DISCORD_TOKEN=your_bot_token_here
```

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
- [x] 🌐 **Multi-server Infrastructure**
  - [x] Support server-specific configurations
- [ ] 🐳 **Containerization Support**
  - [ ] Add Docker compose file and image
- [x] 📝 **Code Optimization**
  - [x] Implement improved runtime logging
  - [x] Implement modular architecture
  - [x] Add comprehensive documentation
- [x] 🇨🇳 **LeetCode.cn Integration**
  - [x] Add slash command `/daily_cn` for LeetCode.cn daily challenge
  - [ ] Implement separate scheduler for LeetCode.cn challenges
- [ ] 🗄️ **Database Integration**
  - [ ] Store and query problem information in database
  - [ ] Enable historical daily challenge lookup
- [ ] 📊 **User Engagement Features**
  - [x] Track submission records of specific users
  - [ ] Allow users to configure tracked LeetCode accounts
  - [ ] Implement server-wide submission leaderboards
- [ ] 🌍 **Internationalization**
  - [ ] Support multiple display languages

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📦 Dependencies

- [discord.py](https://github.com/Rapptz/discord.py) - Discord bot framework
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management
- [requests](https://github.com/psf/requests) - HTTP library for API calls
- [pytz](https://github.com/stub42/pytz) - Timezone handling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.