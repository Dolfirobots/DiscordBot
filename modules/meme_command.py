import disnake
from disnake.ext import commands, tasks
import aiohttp

from logger import logger
import main

CACHED_CHANNELS = []
CACHED_ALLOWED_ROLES = [1436724428598804666, 1436724428728696903, 1436724409418256535] # TODO: Load developer roles from config

class MemeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_cache.start()

    async def check_permissions(self, ctx):
        global CACHED_ALLOWED_ROLES
        user_role_ids = [role.id for role in ctx.author.roles]
        if not any(role_id in user_role_ids for role_id in CACHED_ALLOWED_ROLES):
            return False
        return True

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=15)
    async def update_cache(self):
        global CACHED_CHANNELS, CACHED_ALLOWED_ROLES
        
        data = await main.MAIN_CONFIG.load_json()
        CACHED_CHANNELS = data.get("memes", {}).get("channels", [])
        #CACHED_ALLOWED_ROLES = data.get("memes", {}).get("allowed_roles", [])

    @commands.slash_command(description="Send a random meme from Reddit")
    async def meme(self, inter: disnake.ApplicationCommandInteraction):
        url = "https://meme-api.com/gimme"

        if not CACHED_CHANNELS:
            embed = main.ERROR_EMBED.copy()
            embed.description = "Meme commands are currently disabled everywhere."
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        if inter.channel_id not in CACHED_CHANNELS:
            mention_list = [f"<#{channel_id}>" for channel_id in CACHED_CHANNELS]
            embed = main.ERROR_EMBED.copy()
            embed.description = f"This command can only be used in following channels: {', '.join(mention_list)}!"
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        await inter.response.send_message("*Loading meme...*")

        async with aiohttp.ClientSession() as session:
            attempts = 0
            max_attempts = 10
            
            while attempts < max_attempts:
                attempts += 1
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await inter.edit_original_response(embed=main.ERROR_EMBED)
                        return
                    
                    data = await resp.json()
                    if not data.get("nsfw", False):
                        break
                    logger.warning(f"Skipped NSFW meme (Attempt {attempts}/{max_attempts})", "MemeAPI")

            if data.get("nsfw", True):
                await inter.edit_original_response(embed=main.ERROR_EMBED)
                return

        embed = disnake.Embed(
            title=data["title"], 
            color=disnake.Color.random() 
        )
        embed.set_image(url=data["url"]) 
        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}") 

        embed.set_author(
            name=f"u/{data['author']}", 
            icon_url="https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png",
            url=f"https://reddit.com/u/{data['author']}"
        )

        await inter.edit_original_response(content=None, embed=embed)
    
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
            data["memes"] = {"channels": []}
        
        channels = data["memes"]["channels"]
        channel_id = ctx.channel.id

        if channel_id not in channels:
            channels.append(channel_id)
            data["memes"]["channels"] = channels
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
        
        channels = data.get("memes", {}).get("channels", [])
        channel_id = ctx.channel.id

        if channel_id in channels:
            channels.remove(channel_id)
            data["memes"]["channels"] = channels
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
