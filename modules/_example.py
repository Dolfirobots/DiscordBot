import disnake
from disnake.ext import commands

# Use a good name for the module
class ExampleModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Add your commands and listeners here
    # You need to call the function the same as you want the command to be called in Discord
    # Command example:
    @commands.slash_command(description="Test response time")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        # Do sth here
        await inter.response.send_message(f"It took {round(self.bot.latency * 1000)}ms to respond!")

    # Here is a event example
    # The function must called the same as the event you want to listen to
    # A list of all events can be found here: https://docs.disnake.dev/en/stable/api/events.html
    # Listener example:
    @commands.Cog.listener()
    async def on_message(self, message):
        # Avoid responding to the bot
        if message.author == self.bot.user:
            return
        
        # Some chat command example
        if "hello" in message.content.lower():
            await message.channel.send(f"Hello, {message.author.mention}!")

# Setup function to add the module to the bot
# Do not change this function
# You can add more lines but do not remove the function itself
def setup(bot):
    bot.add_cog(ExampleModule(bot))