# cogs/core_cog.py
import discord
from discord.ext import commands

class CoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        # 如果你的 bot 也處理前綴指令，保留這行
        await self.bot.process_commands(message) 
        self.logger.debug(f"CoreCog: Processed message from {message.author.name}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CoreCog(bot))