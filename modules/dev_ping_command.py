import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands

class PingModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Test response time")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(f"It took {round(self.bot.latency * 1000)}ms to respond!")

def setup(bot):
    bot.add_cog(PingModule(bot))