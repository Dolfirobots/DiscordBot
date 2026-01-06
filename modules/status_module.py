import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands, tasks

from minecraft.status import get_server_status

class StatusModule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.mc_ip = "Dolfirobots.net"
        self.mc_port = 25565
        self.update_mc_status.start()

    def cog_unload(self):
        self.update_mc_status.cancel()

    @tasks.loop(seconds=10)
    async def update_mc_status(self):
        status = await get_server_status(self.mc_ip, self.mc_port, timeout=5)
        
        if status:
            online = status.get("players_online", 0)
            max = status.get("players_max", 0)
            activity = disnake.Activity(
                type=disnake.ActivityType.watching, 
                name=f"{self.mc_ip}: {online}/{max}"
            )

        else:
            activity = disnake.Activity(
                type=disnake.ActivityType.competing, 
                name="🔴 Offline"
            )
        
        await self.bot.change_presence(activity=activity)
    @update_mc_status.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(StatusModule(bot))