# LeetCode Daily Challenge Discord Bot

This is a bot that automatically fetches the LeetCode daily challenge and sends it to a Discord channel.

## Features

- Automatically fetches the LeetCode daily challenge
- Sends the daily challenge to a Discord channel at a specified time
- Supports a manual trigger feature, using the `!leetcode` command
- The challenge information includes: title, difficulty, link, tags, etc.

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
   - Edit `.env` and fill in your Discord bot token and channel ID

3. Run the bot
   ```
   uv run discord_bot.py
   ```

## Usage

### Fetch LeetCode daily challenge

Run `leetcode_daily.py` by itself to fetch and display today's LeetCode daily challenge, and save the result to a JSON file:

```
uv run leetcode_daily.py
```

### Run the Discord bot

Run `discord_bot.py` to start the Discord bot.

```
uv run discord_bot.py
```

### Manually trigger the daily challenge

Run `!leetcode` in the Discord channel to manually trigger the daily challenge.

## TODO

- [x] Add slash command hint to the bot
- [x] Reply at the same channel when the slash command is used
- [ ] Set the notification channel for Admin users
- [ ] Set the notification message and role for Admin users

