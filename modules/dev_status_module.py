import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import disnake
from disnake.ext import commands, tasks

from minecraft.status import get_server_status

class StatusModule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.mc_ip = "mc.hypixel.net"
        self.mc_port = 25565
        self.update_mc_status.start()

    def cog_unload(self):
        self.update_mc_status.cancel()

    @tasks.loop(seconds=10)
    async def update_mc_status(self):
        status = await get_server_status(self.mc_ip, self.mc_port, timeout=5)

        if status:
            online = status.get("players_online", 0)
            max_p = status.get("players_max", 0)
            motd = status.get("plain_description", "Minecraft Server")
            version = status.get("version_name", "1.20.x")

        activity = disnake.Activity(
            application_id=25565,
            name="Test",
            type=disnake.ActivityType.playing,
            state="State",
            details="Details",
            assets={
                "large_image": "server_icon",
                "small_image": "online_dot",
            },
            party={
                "id": 1222,
                "size": (1, 5)
            }
        )

        await self.bot.change_presence(activity=activity)

    @update_mc_status.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(StatusModule(bot))