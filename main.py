import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

import disnake
import os
import argparse

from disnake.ext import commands
from dotenv import load_dotenv

from logger import logger, LogLevel, CURRENT_LOG_LEVEL

# Load config from .env file
load_dotenv()

# Project variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TICKET_DISCORD_TOKEN = os.getenv("TICKET_DISCORD_TOKEN")

TICKET_MODE = False
DEVLEOPER_MODE = False

# Bot configuration
intents = disnake.Intents.default()
intents.message_content = True
intents.members = True

# Bot
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            command_sync_flags=commands.CommandSyncFlags.all(),
        )

    async def on_ready(self):
        if TICKET_MODE:
            logger.success(f"Ticket Bot logged in as \"{self.user}\" ({self.user.id})")
        else:
            logger.success(f"Logged in as \"{self.user}\" ({self.user.id})")

    # Loading modules
    def load_modules(self):
        logger.info("Loading modules...")
        for filename in os.listdir("./modules" if not TICKET_MODE else "./ticket_modules"):
            # ignoring _ files
            if filename.endswith(".py") and not filename.startswith("_") and (DEVLEOPER_MODE or not filename.startswith("dev_")):
                try:
                    self.load_extension(f"modules.{filename[:-3]}")
                    logger.success(f"Loaded module: {filename}")
                except Exception as e:
                    logger.error(f"Error loading module {filename}: {e}")
        logger.info("Finished loading modules.")
        logger.info(f"Total modules loaded: {len(self.extensions)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Dolfirobots Network Discord Bot',
        description='A Discord bot for Dolfirobots Network Discord server'
    )

    parser.add_argument("-l", "--log", "--loglevel", type=str, default="INFO", help="Set the logging level (OFF, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--dev", action="store_true", help="Run the bot in developer mode")
    parser.add_argument("--ticket", action="store_true", help="Run the ticket bot instead of the main bot")

    args = parser.parse_args()

    CURRENT_LOG_LEVEL = LogLevel.from_string(args.log)

    if args.log.upper() not in LogLevel.NAMED_LEVELS.values():
        logger.warning(f"Invalid log level '{args.log}' specified. Falling back to INFO level.")

    DEVLEOPER_MODE = args.dev

    if DEVLEOPER_MODE:
        logger.info("Running in developer mode. Developer modules will be loaded.")

    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is not set in the environment variables.")
        exit(1)

    if args.ticket:
        if not TICKET_DISCORD_TOKEN:
            logger.critical("TICKET_DISCORD_TOKEN is not set in the environment variables.")
            exit(1)
        logger.info("Starting Ticket Bot...")
        TICKET_MODE = True
        DISCORD_TOKEN = TICKET_DISCORD_TOKEN
        
    bot = Bot()
    bot.load_modules()
    bot.run(DISCORD_TOKEN)