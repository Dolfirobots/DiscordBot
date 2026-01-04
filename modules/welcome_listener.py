import disnake
from disnake.ext import commands
import random

from config import Config, FileType
from logger import logger

# Variables
WELCOME_CONFIG = Config("welcome_messages.txt", FileType.TXT)
LEAVE_CONFIG = Config("leave_messages.txt", FileType.TXT)


class EventListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        await WELCOME_CONFIG.validate()
        await LEAVE_CONFIG.validate()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel:
            embed = disnake.Embed(
                description=f"Welcome to our server, {member.mention}!"
                            f"\n - Total Members: **{member.guild.member_count}**"
                            f"\n - Account Created: {disnake.utils.format_dt(member.created_at, style='R')}",
                color=0x2ecc71,
                timestamp=disnake.utils.utcnow()
            )

            raw_message = await get_welcome_message()

            try:
                formatted_name = raw_message % member.display_name
            except TypeError as e:
                logger.warning(f"Welcome message formatting failed, using fallback. Message: {raw_message}, Error: {e}")
                formatted_name = f"{member.display_name} just joined us!"

            embed.set_author(
                name=formatted_name,
                icon_url=member.display_avatar.url
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            embed.set_footer(
                text=f"{member.guild.name}",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = member.guild.system_channel
        if channel:
            embed = disnake.Embed(
                description=f"{member.display_name} has left the server."
                            f"\n - Total Members: **{member.guild.member_count}**",
                color=0xe74c3c,
                timestamp=disnake.utils.utcnow()
            )

            raw_message = await get_leave_message()

            try:
                formatted_name = raw_message % member.display_name
            except TypeError as e:
                logger.warning(f"Leave message formatting failed, using fallback. Message: {raw_message}, Error: {e}")
                formatted_name = f"{member.display_name} just left us!"

            embed.set_author(
                name=formatted_name,
                icon_url=member.display_avatar.url
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            embed.set_footer(
                text=f"{member.guild.name}",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            
            await channel.send(embed=embed)

async def get_welcome_message():
    try:
        await WELCOME_CONFIG.validate()
        lines = await WELCOME_CONFIG.get_lines()

        if not lines:
            logger.warning("Welcome file is empty! Using fallback.")
            return "%s just joined us!"
        
        return random.choice(lines)
    except Exception as e:
        return "%s just joined us!"
    
async def get_leave_message():
    try:
        await LEAVE_CONFIG.validate()
        lines = await LEAVE_CONFIG.get_lines()

        if not lines:
            logger.warning("Leave file is empty! Using fallback.")
            return "%s just left us!"
        
        return random.choice(lines)
    except Exception as e:
        return "%s just left us!"

def setup(bot):
    bot.add_cog(EventListener(bot))