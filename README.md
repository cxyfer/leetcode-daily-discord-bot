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
   git clone https://github.com/your-username/leetcode-daily-discord-bot.git
   cd leetcode-daily-discord-bot
   ```

2. Install the dependencies
   ```
   uv pip install -r requirements.txt
   ```

3. Configure the environment variables
   - Copy `.env.example` to `.env`
   - Edit `.env` and fill in your Discord bot token and channel ID

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

- [ ] Add a command hint to the bot
- [ ] Set the group ID for Admin users
- [ ] Set the group ID for Admin users

