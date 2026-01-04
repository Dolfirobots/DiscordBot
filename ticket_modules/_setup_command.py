import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands

ADMIN_ROLE_ID = 1436724409418256535

class SetupTicket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if message.content.lower() == "!ticket setup":
            if not any(role.id == ADMIN_ROLE_ID for role in message.author.roles):
                await message.channel.send("You do not have permission to use this command.")
                return
            
            embed = disnake.Embed(
                title="Ticket System Setup",
                description="React with 🎫 to create a ticket.",
                color=disnake.Color.blue()
            )

            await message.channel.send(embed=embed, view=TicketView())

        await self.bot.process_commands(message)


def setup(bot):
    bot.add_cog(SetupTicket(bot))