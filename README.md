# LeetCode Daily Challenge Discord Bot

This is a bot that automatically fetches the LeetCode daily challenge and sends it to a Discord channel.

## Features

- Automatically retrieves the LeetCode daily challenge
- Sends the daily challenge to the Discord channel at a specified time
- Supports manual triggering using the `/daily` slash command
- Daily challenge information includes: title, difficulty, link, tags, etc.
- Supports multi-server configuration, each server can set its own notification channel, role to mention, and delivery time

## Installation

1. Clone this repository
   ```
   git clone https://github.com/cxyfer/leetcode-daily-discord-bot.git
   cd leetcode-daily-discord-bot
   ```

2. Configure the environment variables
   - Copy `.env.example` to `.env`
   ```
   mv .env.example .env
   ```
   - Edit `.env` and enter your Discord bot token

3. Run the bot
   ```
   uv run discord_bot.py
   ```

## Usage

### Slash Commands

The bot provides the following slash commands:

- `/daily` - Manually display today's LeetCode daily challenge
- `/set_channel` - Set the channel for the bot to send daily challenges (requires channel management permissions)
- `/set_role` - Set the role for the bot to mention (requires role management permissions)
- `/set_post_time` - Set the time to send the daily challenge, format HH:MM (requires server management permissions)
   - The post time is actually HH:MM:10 to avoid getting yesterday's question information. 
- `/set_timezone` - Set the timezone, e.g., Asia/Taipei (requires server management permissions)
- `/show_settings` - Display the current server settings
- `/remove_channel` - Remove the channel setting, stopping daily challenges (requires server management permissions)

### Server-specific Settings

Each Discord server can have its own independent settings:

1. Using `/set_channel` to set the channel is the first step, this **must be completed first**
2. Use `/set_role` to set the role to mention (optional)
3. Use `/set_post_time` and `/set_timezone` to set the delivery time and timezone (optional)
4. Use `/show_settings` to view current settings

The bot will automatically schedule the delivery of daily challenges according to each server's settings.

## Development Roadmap

- [x] Add slash command prompts
- [x] Reply in the same channel where slash commands are used
- [x] Allow admin users to set the configuration, including the notification channel, role to mention, and delivery time
- [x] Support multi-server configuration
- [ ] More readable runtime logs
- [ ] Add Docker compose file and image
- [ ] Refactor the code to be more readable and maintainable
- [ ] Support LeetCode.cn
- [ ] Query problem information from the database
- [ ] Query the past daily challenge from the database
- [ ] Allow users to set the account to trace submission records
- [ ] Add ranking of submission records of each server
- [ ] Support different display languages