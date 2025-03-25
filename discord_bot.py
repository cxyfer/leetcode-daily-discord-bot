import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path

from leetcode_daily import fetch_raw_data, extract_challenge_info

load_dotenv(dotenv_path='.env', verbose=True, override=True)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
POST_TIME = os.getenv('POST_TIME', '00:00')  # Default to 00:00
TIMEZONE = os.getenv('TIMEZONE', 'UTC')  # Default to UTC
GROUP_ID = os.getenv('GROUP_ID')  # Group ID

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True  # Enable message content permission
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """When the bot successfully connects to Discord"""
    slash = await bot.tree.sync()  # Sync slash commands
    
    print(f'{bot.user} has connected to Discord!')
    print(f'The bot will send the LeetCode daily challenge at {POST_TIME} ({TIMEZONE} timezone)')
    print(f'Loaded {len(slash)} slash commands')
    
    # Start the daily schedule task
    await schedule_daily_challenge()

async def schedule_daily_challenge():
    """Schedule daily sending of LeetCode challenges"""
    while True:
        # Get the current time in the specified timezone
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)
        
        # Parse the scheduled sending time
        hour, minute = map(int, POST_TIME.split(':'))
        
        # Calculate the next sending time
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target_time:
            # If the current sending time has passed, set it to the same time tomorrow
            target_time = target_time + timedelta(days=1)
        
        # Calculate the waiting time (seconds)
        wait_seconds = (target_time - now).total_seconds()
        print(f'The next sending will be at {target_time} ({TIMEZONE} timezone), waiting {wait_seconds / 60:.2f} minutes')
        
        # Wait until the specified time
        await asyncio.sleep(wait_seconds)
        
        # Get the channel and tag the LC role
        channel = bot.get_channel(CHANNEL_ID)
        if channel and GROUP_ID:
            await channel.send(f"<@&{GROUP_ID}>") 
            
        # Send the daily challenge
        await send_daily_challenge()

async def send_daily_challenge(interaction=None):
    """Get and send the LeetCode daily challenge to the Discord channel"""
    try:
        # Get the current date to create the file path
        timezone = pytz.timezone("UTC")  # **Fix timezone to UTC**
        now = datetime.now(timezone)
        date_str = now.strftime("%Y-%m-%d")
        yy, mm, _ = date_str.split('-')
        
        # Create the file path and directory
        file_dir = Path(f"data/daily/{yy}/{mm}")
        file_path = file_dir / f"{date_str}.json"
        
        # Check if there is already a file for today
        info = None
        if file_path.exists():
            print(f"Found existing challenge data at {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
            except Exception as e:
                print(f"Error reading existing file: {e}")
                info = None
        
        # If no valid file is found, fetch the data
        if info is None:
            print("Fetching new challenge data...")
            challenge_data = fetch_raw_data()
            info = extract_challenge_info(challenge_data)
            file_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print(f"Challenge data saved to {file_path}")
        
        # Format the information
        title = info['title']
        difficulty = info['difficulty']
        link = info['link']
        qid = info['qid']
        date = info['date']
        
        # Set the color based on the difficulty
        color_map = {
            'Easy': 0x00FF00,  # Green
            'Medium': 0xFFA500,  # Orange
            'Hard': 0xFF0000,  # Red
        }
        emoji_map = {
            'Easy': '🟢',
            'Medium': '🟡',
            'Hard': '🔴',
        }
        embed_color = color_map.get(difficulty, 0x0099FF)
        
        # Create a Discord embed message
        embed = discord.Embed(
            title=f"{qid}. {title}",
            color=embed_color,
            url=link
        )
        
        # Add fields
        embed.add_field(name="Difficulty", value=difficulty, inline=True)
        embed.add_field(name="Rating", value=f"|| {round(info['rating'])} ||", inline=True)
        if info['tags']:
            tags = ", ".join([f"||{tag}||" for tag in info['tags']])
            embed.add_field(name="Tags", value=tags, inline=True)
        
        embed.set_footer(text=f"LeetCode Daily Challenge | {info['date']}")
        
        # Determine how to send the message based on whether there is an interaction object
        if interaction:
            await interaction.followup.send(embed=embed)
            print(f"Sent LeetCode daily challenge as response to slash command")
        else:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(embed=embed)
                print(f"Sent LeetCode daily challenge to channel {CHANNEL_ID}")
            else:
                print(f"Failed to get channel {CHANNEL_ID}")
    
    except Exception as e:
        print(f"Error sending daily challenge: {e}")
        if interaction:
            await interaction.followup.send("An error occurred, unable to fetch the LeetCode daily challenge.")

@bot.tree.command(name="daily", description="Get today's LeetCode daily challenge")
async def daily_command(interaction: discord.Interaction):
    """Slash command to get today's LeetCode challenge"""
    await interaction.response.defer()  # Defer the response, because fetching data may take some time
    await send_daily_challenge(interaction=interaction)

@bot.event
async def on_message(message):
    """Process user messages"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Keep the original command functionality
    await bot.process_commands(message)

# Run the bot
def run_bot():
    """Run the Discord bot"""
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_bot() 