import asyncio
import disnake
from disnake.ext import commands, tasks
import time
import aiohttp
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger
import main
from utils import ErrorEmbed, FooterEmbed

CACHED_CHANNELS = []

class MemeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_cache.start()

    async def check_permissions(self, ctx):
        data = await main.MAIN_CONFIG.load_json()
        user_role_ids = [role.id for role in ctx.author.roles]
        if not any(role_id in user_role_ids for role_id in data.get("roles", {}).get("admin", [])):
            return False
        return True

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=15)
    async def update_cache(self):
        global CACHED_CHANNELS
        
        data = await main.MAIN_CONFIG.load_json()
        CACHED_CHANNELS = data.get("memes", {}).get("allowed_channels", [])

    @commands.slash_command(description="Send a random meme from Reddit")
    async def meme(self, inter: disnake.ApplicationCommandInteraction):
        ns_time = time.time_ns()
        url = "https://meme-api.com/gimme"

        if not CACHED_CHANNELS:
            embed = ErrorEmbed(
                "Meme commands are currently disabled everywhere.",
                time=time.time_ns() - ns_time,
                service="Memes"
            )
            await inter.response.send_message(embed=embed, ephemeral=True, delete_after=5)
            return

        if inter.channel_id not in CACHED_CHANNELS:
            mention_list = [f"<#{channel_id}>" for channel_id in CACHED_CHANNELS]
            embed = ErrorEmbed(
                f"This command can only be used in following channels: {', '.join(mention_list)}!",
                time=time.time_ns() - ns_time,
                service="Memes"
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        data = await main.MAIN_CONFIG.load_json()
        loading_icon = data.get("emojis", {}).get("loading")

        loading_icon = loading_icon if loading_icon else "🔄️"
        
        await inter.response.send_message(f"{loading_icon} *Loading meme...*")

        async with aiohttp.ClientSession() as session:
            attempts = 0
            max_attempts = 10
            timeout = aiohttp.ClientTimeout(total=6)

            # Skipping NSFW content
            while attempts < max_attempts:
                attempts += 1
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        if resp.status != 200:
                            await inter.edit_original_response(content=None, embed=ErrorEmbed())
                            return
                        
                        data = await resp.json()
                        if not data.get("nsfw", False):
                            break
                            
                except asyncio.TimeoutError:
                    logger.error("Took too long to request a meme (Timeout)", "Meme Command")
                    await inter.edit_original_response(content=None, embed=ErrorEmbed(
                        "API is probaly down. Check later again.",
                        service="Memes",
                        time=time.time_ns() - ns_time
                    ))
                    return
                except Exception as e:
                    logger.error(f"Connection error: {e}", "Meme Command")
                    await inter.edit_original_response(content=None, embed=ErrorEmbed(
                        time=time.time_ns() - ns_time,
                        service="Memes"
                    ))
                    return

        embed = disnake.Embed(
            title=data["title"], 
            color=disnake.Color.random() 
        )
        embed.set_image(url=data["url"]) 

        embed = FooterEmbed(
            embed=embed,
            text=f"👍 {data['ups']}  |  u/{data['author']}",
            time=time.time_ns() - ns_time,
            service="Memes"
        )
        embed.set_author(
            name=f"r/{data['subreddit']}", 
            icon_url="https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
            url=f"https://reddit.com/r/{data['subreddit']}"
        )

        logger.info(f"Generated a meme by @{inter.author.name} ({inter.author.mention})")
        await inter.edit_original_response(content=None, embed=embed)
    
    # Deprecated
    @commands.group(name="memes", invoke_without_command=True)
    async def memes(self, ctx: commands.Context):
        if not await self.check_permissions(ctx):
            return
        await ctx.message.delete()
        await ctx.send("Usage: `!memes channel <add|remove>`", delete_after=4)

    @memes.group(name="channel", invoke_without_command=True)
    async def channel(self, ctx: commands.Context):
        if not await self.check_permissions(ctx):
            return
        await ctx.message.delete()
        await ctx.send("Usage: `!memes channel <add|remove>`", delete_after=4)

    @channel.command(name="add")
    async def channel_add(self, ctx: commands.Context):
        if not await self.check_permissions(ctx):
            return
        await ctx.message.delete()

        config = main.MAIN_CONFIG
        data = await config.load_json()
        
        if "memes" not in data:
            data["memes"] = {"allowed_channels": []}
        
        channels = data["memes"]["allowed_channels"]
        channel_id = ctx.channel.id

        if channel_id not in channels:
            channels.append(channel_id)
            data["memes"]["allowed_channels"] = channels
            await config.save_json(data)
            
            global CACHED_CHANNELS
            CACHED_CHANNELS = channels
            
            embed = main.SUCCESS_EMBED.copy()
            embed.description = f"`/meme` can now be used in {ctx.channel.mention}!"
        else:
            embed = main.ERROR_EMBED.copy()
            embed.description = "This channel is already added."

        await ctx.send(embed=embed, delete_after=6)

    @channel.command(name="remove")
    async def channel_remove(self, ctx: commands.Context):
        if not await self.check_permissions(ctx):
            return
        await ctx.message.delete()

        config = main.MAIN_CONFIG
        data = await config.load_json()
        
        channels = data.get("memes", {}).get("allowed_channels", [])
        channel_id = ctx.channel.id

        if channel_id in channels:
            channels.remove(channel_id)
            data["memes"]["allowed_channels"] = channels
            await config.save_json(data)

            global CACHED_CHANNELS
            CACHED_CHANNELS = channels
            
            embed = main.SUCCESS_EMBED.copy()
            embed.description = f"`/meme` is no longer allowed in {ctx.channel.mention}!"
        else:
            embed = main.ERROR_EMBED.copy()
            embed.description = "This channel was not in the list."

        await ctx.send(embed=embed, delete_after=6)

def setup(bot):
    bot.add_cog(MemeCommand(bot))
