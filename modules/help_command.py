import sys
import os
import time

from utils import FooterEmbed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands

class HelpModule(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.slash_command(description="Sends a help message")
    async def help(self, inter: disnake.ApplicationCommandInteraction):
        ns_time = time.time_ns()
        await inter.response.defer()

        embed = disnake.Embed(
            title="Help Center",
            description=f"Hello {inter.author.display_name}! Here is a list of available modules and system status.",
            color=0x2b2d31,
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="🛰️ General Commands",
            value=(
                "`/help` - Shows this interface\n"
                "`/meme` - Sends a cool meme from Reddit"
            ),
            inline=True
        )

        embed.add_field(
            name="📊 System Status",
            value=(
                f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
                "**Ticket System:** `Active`"
            ),
            inline=True
        )

        embed = FooterEmbed(
            embed=embed,
            time=time.time_ns() - ns_time,
            service="Help",
            icon_url=self.bot.user.avatar.url
        )
        await inter.edit_original_message(embed=embed)

    @commands.command("help")
    async def help(self, ctx: commands.Context):
        ns_time = time.time_ns()

        embed = disnake.Embed(
            title="Help Center",
            description=f"Hello {ctx.author.display_name}! Here is a list of available modules and system status.",
            color=0x2b2d31,
            timestamp=disnake.utils.utcnow()
        )

        embed.add_field(
            name="🛰️ General Commands",
            value=(
                "`/help` - Shows this interface\n"
                "`/meme` - Sends a random meme from Reddit"
            ),
            inline=True
        )

        embed.add_field(
            name="📊 System Status",
            value=(
                f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
                "**Ticket System:** `Active`"
            ),
            inline=True
        )

        embed = FooterEmbed(
            embed=embed,
            time=time.time_ns() - ns_time,
            service="Help",
            icon_url=self.bot.user.avatar.url
        )
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(HelpModule(bot))