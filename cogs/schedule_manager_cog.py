# cogs/schedule_manager_cog.py
import os

import pytz
from discord.ext import commands
from utils.logger import get_scheduler_logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import UI helpers
from utils.ui_helpers import send_daily_challenge

# Default values, similar to how they are defined in bot.py
DEFAULT_POST_TIME = os.getenv("POST_TIME", "00:00")
DEFAULT_TIMEZONE = os.getenv("TIMEZONE", "UTC")


class ScheduleManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_scheduler_logger()

        # Setup APScheduler (uses MemoryJobStore by default, avoiding Discord object serialization issues)
        job_defaults = {
            "coalesce": False,
            "max_instances": 3,
            "misfire_grace_time": 300,  # 5 minutes grace time
        }

        self.scheduler = AsyncIOScheduler(job_defaults=job_defaults, timezone=pytz.UTC)

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
                self.logger.warning(
                    f"Server settings found with no server_id: {server_settings}"
                )
                continue

            if not server_settings.get("channel_id"):
                self.logger.info(
                    f"Server {server_id} has no channel_id set, skipping schedule."
                )
                continue

            await self.add_server_schedule(server_settings)
            count += 1

        self.logger.info(f"Total {count} server schedules created with APScheduler.")

    async def add_server_schedule(self, server_settings):
        """Add schedule for a single server using APScheduler"""
        server_id = server_settings.get("server_id")
        channel_id = server_settings.get("channel_id")

        if not channel_id:
            self.logger.error(
                f"Attempted to schedule for server {server_id} but no channel_id was provided."
            )
            return

        post_time_str = server_settings.get("post_time", DEFAULT_POST_TIME)
        timezone_str = server_settings.get("timezone", DEFAULT_TIMEZONE)
        role_id = server_settings.get("role_id")

        try:
            hour, minute = map(int, post_time_str.split(":"))
            target_timezone = pytz.timezone(timezone_str)

            # Create cron trigger for daily execution
            trigger = CronTrigger(hour=hour, minute=minute, timezone=target_timezone)

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
                name=f"Daily Challenge for Server {server_id}",
            )

            self.logger.info(
                f"Scheduled daily challenge for server {server_id} at {post_time_str} {timezone_str}"
            )

        except ValueError as e:
            self.logger.error(
                f"Server {server_id}: Invalid post_time format '{post_time_str}': {e}"
            )
        except Exception as e:
            self.logger.error(
                f"Server {server_id}: Error adding schedule: {e}", exc_info=True
            )

    async def send_daily_challenge_job(
        self, server_id: int, channel_id: int, role_id: int = None
    ):
        """Job function called by APScheduler to send daily challenges"""
        try:
            self.logger.info(
                f"APScheduler triggered: Sending daily challenge for server {server_id}"
            )

            # Send the daily challenge
            challenge_info = await send_daily_challenge(
                bot=self.bot,
                channel_id=channel_id,
                role_id=role_id,
            )

            if challenge_info:
                self.logger.info(
                    f"Successfully sent daily challenge for server {server_id}: {challenge_info.get('title')}"
                )
            else:
                self.logger.warning(
                    f"Failed to send daily challenge for server {server_id}"
                )

        except Exception as e:
            self.logger.error(
                f"Error in send_daily_challenge_job for server {server_id}: {e}",
                exc_info=True,
            )

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
                self.logger.info(
                    f"Server {server_id} daily challenge has been rescheduled"
                )
            else:
                self.logger.info(
                    f"Server {server_id} has no valid settings, schedule removed"
                )
        else:
            self.logger.info("Rescheduling daily challenges for ALL servers...")
            # Remove all existing jobs
            self.scheduler.remove_all_jobs()
            # Re-initialize all schedules
            await self.initialize_schedules()
            self.logger.info("All server daily challenges have been rescheduled")

    def get_scheduled_jobs(self):
        """Get information about all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    async def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if hasattr(self, "scheduler") and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info("APScheduler shutdown complete")


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleManagerCog(bot))
