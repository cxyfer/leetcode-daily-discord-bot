# cogs/core_cog.py
import discord
from discord.ext import commands

from bot.utils.logger import get_commands_logger


class CoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        self.logger.debug(f"CoreCog: Observed message from {message.author.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(CoreCog(bot))
