# Give your module a descriptive name
# For example, if the module handles a ping command, you could name it welcome_listener.py
# The name is always in snake_case written
# Give the the file a suffix:
# *_command.py  : if it mainly contains commands
# *_listener.py : if it mainly contains event listeners
# *_module.py   : if it contains a mix of both commands and listeners or other functionalities
# Add a prefix:
# _*    : for ignoring the module during loading
# dev_* : modules are only loaded in developer mode (if you add the --dev argument when starting the bot)

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # Replace .. with the correct path if needed

import disnake
from disnake.ext import commands

# The class name should also reflect the module's functionality
# Use CamelCase for class names
class ExampleModule(commands.Cog):
    # Your class variables
    def __init__(self, bot):
        self.bot = bot

    # Add here you init code if needed
    @commands.Cog.listener()
    async def on_ready(self):
        print("ExampleModule is ready!")

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
# You can add your init code in the on_ready function
def setup(bot):
    bot.add_cog(ExampleModule(bot))