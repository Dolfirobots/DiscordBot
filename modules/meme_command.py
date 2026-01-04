import disnake
from disnake.ext import commands
import aiohttp

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Sendet ein Meme von Reddit")
    async def meme(self, inter: disnake.ApplicationCommandInteraction):
        url = "https://meme-api.com/gimme"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        embed = disnake.Embed(
            title=data["title"], 
            color=disnake.Color.random() 
        )
        embed.set_image(url=data["url"]) 
        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}") 

        await inter.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(Utility(bot))
