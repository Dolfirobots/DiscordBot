import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands

import config

ADMIN_ROLE_ID = 1436724409418256535
TICKET_CONFIG = config.Config("ticket_config.json", config.FileType.JSON)

NO_PERMISSION_EMBED = disnake.Embed(
    title="Error",
    description="You do not have permission to use this command.",
    color=disnake.Color.red()
)

class AdminTicketCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await TICKET_CONFIG.validate()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if message.content.lower() == "!ticket setup":
            if not any(role.id == ADMIN_ROLE_ID for role in message.author.roles):
                await message.channel.send(embed = NO_PERMISSION_EMBED, ephemeral=True)
                return
            
            config = TICKET_CONFIG.load_json()
            config["ticket_create_channel"] = message.channel.id
            TICKET_CONFIG.save_json(config)
            embed = disnake.Embed(
                title="Ticket Create Channel successfully set!",
                description="Ticket Create Channel is now <#{}>.".format(message.channel.id),
                color=disnake.Color.green()
            )
            
            await message.channel.send(embed=embed, ephemeral=True)
            await message.delete()


def setup(bot):
    bot.add_cog(AdminTicketCommand(bot))