import time
import disnake
from disnake.ext import commands
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import SuccessEmbed

class PingModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Test response time")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        ns_time = time.time_ns()
        await inter.response.send_message(embed=SuccessEmbed(f"It took `{round(self.bot.latency * 1000)}ms` to respond!", time=time.time_ns() - ns_time))


def setup(bot):
    bot.add_cog(PingModule(bot))