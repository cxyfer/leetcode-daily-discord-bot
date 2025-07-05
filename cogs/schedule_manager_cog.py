# cogs/schedule_manager_cog.py
import asyncio
import discord
from discord.ext import commands
import pytz
from datetime import datetime, timedelta
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Default values, similar to how they are defined in bot.py
DEFAULT_POST_TIME = os.getenv('POST_TIME', '00:00')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'UTC')

class ScheduleManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger
        
        # Setup APScheduler (uses MemoryJobStore by default, avoiding Discord object serialization issues)
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5 minutes grace time
        }
        
        self.scheduler = AsyncIOScheduler(
            job_defaults=job_defaults,
            timezone=pytz.UTC
        )

    async def initialize_schedules(self):
        """
        Initialize daily LeetCode challenge schedules for all servers.
        
        Note: Uses MemoryJobStore which means:
        - Jobs are lost on bot restart (but will be recreated from database settings)
        - No persistence issues with Discord object serialization
        - Lightweight and fast for simple recurring tasks
        """
        self.logger.info("Initializing APScheduler-based daily challenge schedules...")
        
        # Start the scheduler
        self.scheduler.start()
        self.logger.info("APScheduler started successfully")
        
        # Clear any existing jobs to avoid duplicates
        self.scheduler.remove_all_jobs()
        
        # Get all server settings and create schedules
        servers = self.bot.db.get_all_servers()
        count = 0
        
        for server_settings in servers:
            server_id = server_settings.get("server_id")
            if not server_id:
                self.logger.warning(f"Server settings found with no server_id: {server_settings}")
                continue
            
            if not server_settings.get("channel_id"):
                self.logger.info(f"Server {server_id} has no channel_id set, skipping schedule.")
                continue

            await self.add_server_schedule(server_settings)
            count += 1
        
        self.logger.info(f"Total {count} server schedules created with APScheduler.")

    async def add_server_schedule(self, server_settings):
        """Add schedule for a single server using APScheduler"""
        server_id = server_settings.get("server_id")
        channel_id = server_settings.get("channel_id")
        
        if not channel_id:
            self.logger.error(f"Attempted to schedule for server {server_id} but no channel_id was provided.")
            return

        post_time_str = server_settings.get("post_time", DEFAULT_POST_TIME)
        timezone_str = server_settings.get("timezone", DEFAULT_TIMEZONE)
        role_id = server_settings.get("role_id")

        try:
            hour, minute = map(int, post_time_str.split(':'))
            target_timezone = pytz.timezone(timezone_str)
            
            # Create cron trigger for daily execution
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=target_timezone
            )
            
            job_id = f"daily_challenge_{server_id}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Add new job
            self.scheduler.add_job(
                func=self.send_daily_challenge_job,
                trigger=trigger,
                id=job_id,
                args=[server_id, channel_id, role_id],
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                name=f"Daily Challenge for Server {server_id}"
            )
            
            self.logger.info(f"Scheduled daily challenge for server {server_id} at {post_time_str} {timezone_str}")
            
        except ValueError as e:
            self.logger.error(f"Server {server_id}: Invalid post_time format '{post_time_str}': {e}")
        except Exception as e:
            self.logger.error(f"Server {server_id}: Error adding schedule: {e}", exc_info=True)

    async def send_daily_challenge_job(self, server_id: int, channel_id: int, role_id: int = None):
        """Job function called by APScheduler to send daily challenges"""
        try:
            self.logger.info(f"APScheduler triggered: Sending daily challenge for server {server_id}")
            
            # Send the daily challenge
            challenge_info = await self.send_daily_challenge(
                channel_id=channel_id,
                role_id=role_id
            )
            
            if challenge_info:
                self.logger.info(f"Successfully sent daily challenge for server {server_id}: {challenge_info.get('title')}")
            else:
                self.logger.warning(f"Failed to send daily challenge for server {server_id}")
                
        except Exception as e:
            self.logger.error(f"Error in send_daily_challenge_job for server {server_id}: {e}", exc_info=True)

    async def reschedule_daily_challenge(self, server_id: int = None):
        """Reschedule the daily challenge for a specific server or all servers"""
        if server_id is not None:
            self.logger.info(f"Rescheduling daily challenge for server {server_id}...")
            
            # Remove existing job for this server
            job_id = f"daily_challenge_{server_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                self.logger.info(f"Removed existing schedule for server {server_id}")
            
            # Get server settings and add new schedule
            server_settings = self.bot.db.get_server_settings(server_id)
            if server_settings and server_settings.get("channel_id"):
                await self.add_server_schedule(server_settings)
                self.logger.info(f"Server {server_id} daily challenge has been rescheduled")
            else:
                self.logger.info(f"Server {server_id} has no valid settings, schedule removed")
        else:
            self.logger.info("Rescheduling daily challenges for ALL servers...")
            # Remove all existing jobs
            self.scheduler.remove_all_jobs()
            # Re-initialize all schedules
            await self.initialize_schedules()
            self.logger.info("All server daily challenges have been rescheduled")

    async def create_problem_embed(self, problem_info: dict, domain: str = "com", is_daily: bool = False, date_str: str = None):
        """Create an embed for a LeetCode problem"""
        color_map = {'Easy': 0x00FF00, 'Medium': 0xFFA500, 'Hard': 0xFF0000}
        emoji_map = {'Easy': '🟢', 'Medium': '🟡', 'Hard': '🔴'}
        embed_color = color_map.get(problem_info['difficulty'], 0x0099FF)

        embed = discord.Embed(
            title=f"🔗 {problem_info['id']}. {problem_info['title']}",
            color=embed_color,
            url=problem_info['link']
        )

        if domain == "com":
            alt_link = problem_info['link'].replace("leetcode.com", "leetcode.cn")
            embed.description = f"Solve on [LCCN (leetcode.cn)]({alt_link})."
        else:
            alt_link = problem_info['link'].replace("leetcode.cn", "leetcode.com")
            embed.description = f"Solve on [LCUS (leetcode.com)]({alt_link})."

        embed.add_field(name="🔥 Difficulty", value=f"**{problem_info['difficulty']}**", inline=True)
        if problem_info.get('rating') and round(problem_info['rating']) > 0:
            embed.add_field(name="⭐ Rating", value=f"**{round(problem_info['rating'])}**", inline=True)
        if problem_info.get('ac_rate'):
            embed.add_field(name="📈 AC Rate", value=f"**{round(problem_info['ac_rate'], 2)}%**", inline=True)
        
        if problem_info.get('tags'):    
            tags_str = ", ".join([f"||`{tag}`||" for tag in problem_info['tags']])
            embed.add_field(name="🏷️ Tags", value=tags_str if tags_str else "N/A", inline=False)
        
        # Similar questions handling (limit to avoid too much processing)
        if problem_info.get('similar_questions'):
            current_client = self.bot.lcus if domain == "com" else self.bot.lccn
            similar_q_list = []
            for sq_slug_info in problem_info['similar_questions'][:3]:
                sq_detail = await current_client.get_problem(slug=sq_slug_info['titleSlug'])
                if sq_detail:
                    sq_text = f"- {emoji_map.get(sq_detail['difficulty'], '')} [{sq_detail['id']}. {sq_detail['title']}]({sq_detail['link']})"
                    if sq_detail.get('rating') and sq_detail['rating'] > 0: 
                        sq_text += f" *{int(sq_detail['rating'])}*"
                    similar_q_list.append(sq_text)
            if similar_q_list:
                embed.add_field(name="🔍 Similar Questions", value="\n".join(similar_q_list), inline=False)

        if is_daily:
            # Use passed date_str or fallback to problem_info date or 'Today'
            display_date = date_str or problem_info.get('date', 'Today')
            embed.set_footer(text=f"LeetCode Daily Challenge | {display_date}", icon_url="https://leetcode.com/static/images/LeetCode_logo.png")
        else:
            embed.set_footer(text="LeetCode Problem", icon_url="https://leetcode.com/static/images/LeetCode_logo.png")

        return embed

    async def create_problem_view(self, problem_info: dict, domain: str = "com"):
        """Create a view with buttons for a LeetCode problem"""
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="題目描述",
            emoji="📖",
            custom_id=f"{self.bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX}{problem_info['id']}_{domain}"
        ))
        if self.bot.llm:
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.success,
                label="LLM 翻譯",
                emoji="🤖",
                custom_id=f"{self.bot.LEETCODE_TRANSLATE_BUTTON_PREFIX}{problem_info['id']}_{domain}"
            ))
        if self.bot.llm_pro:
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="靈感啟發",
                emoji="💡",
                custom_id=f"{self.bot.LEETCODE_INSPIRE_BUTTON_PREFIX}{problem_info['id']}_{domain}"
            ))
        return view

    async def send_daily_challenge(self, channel_id: int = None, role_id: int = None, interaction: discord.Interaction = None, domain: str = "com", ephemeral: bool = True):
        """Fetches and sends the LeetCode daily challenge."""
        try:
            self.logger.info(f"Attempting to send daily challenge. Domain: {domain}, Channel: {channel_id}, Interaction: {'Yes' if interaction else 'No'}")
            
            current_client = self.bot.lcus if domain == "com" else self.bot.lccn
            
            # Determine date string based on LeetCode's server timezone for daily challenges
            now_utc = datetime.now(pytz.UTC)
            date_str = now_utc.strftime("%Y-%m-%d")

            self.logger.debug(f"Fetching daily challenge for date: {date_str} (UTC), domain: {domain}")
            challenge_info = await current_client.get_daily_challenge()

            if not challenge_info:
                self.logger.error(f"Failed to get daily challenge info for domain {domain}.")
                if interaction: 
                    await interaction.followup.send("Could not fetch daily challenge.", ephemeral=ephemeral)
                return None

            self.logger.info(f"Got daily challenge: {challenge_info['id']}. {challenge_info['title']} for domain {domain}")


            embed = await self.create_problem_embed(challenge_info, domain, is_daily=True)
            view = await self.create_problem_view(challenge_info, domain)

            if interaction:
                # If called from a slash command
                await interaction.followup.send(embed=embed, view=view, ephemeral=ephemeral)
                self.logger.info(f"Sent daily challenge via interaction {interaction.id}")
            elif channel_id:
                target_channel = self.bot.get_channel(channel_id)
                if target_channel:
                    content_msg = ""
                    if role_id:
                        # Ensure role exists in guild before mentioning
                        guild = target_channel.guild
                        role = guild.get_role(role_id)
                        if role:
                            content_msg = f"{role.mention}"
                        else:
                            self.logger.warning(f"Role ID {role_id} not found in guild {guild.id} for channel {channel_id}.")
                    await target_channel.send(content=content_msg if content_msg else None, embed=embed, view=view)
                    self.logger.info(f"Sent daily challenge to channel {channel_id}")
                else:
                    self.logger.error(f"Could not find channel {channel_id} to send daily challenge.")
            else:
                self.logger.error("send_daily_challenge called without channel_id or interaction.")

            return challenge_info

        except Exception as e:
            self.logger.error(f"Error in send_daily_challenge: {e}", exc_info=True)
            if interaction:
                try:
                    await interaction.followup.send(f"An error occurred while sending the daily challenge: {e}", ephemeral=ephemeral)
                except:
                    pass
            return None

    def get_scheduled_jobs(self):
        """Get information about all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs

    async def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info("APScheduler shutdown complete")

async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleManagerCog(bot))