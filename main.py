from disnake.ext import commands
from dotenv import load_dotenv
import asyncio
import pathlib
import disnake
import argparse
import getpass
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from logger import logger, LogLevel
from config import Config

load_dotenv()

# Project variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TICKET_DISCORD_TOKEN = os.getenv("TICKET_DISCORD_TOKEN")

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
MAIN_CONFIG = Config("config.json")

DEVELOPER_MODE = False

# Old msg service
ERROR_EMBED = disnake.Embed(
    title="❌ Error",
    description="An unexpected error occurred. Please try again later.",
    color=0xe74c3c
)
SUCCESS_EMBED = disnake.Embed(
    title="✅ Success",
    description="The action was completed successfully.",
    color=0x2ecc71
)
NO_PERMISSION_EMBED = disnake.Embed(
    title="🚫 Permission Denied",
    description="You do not have the required permissions to use this command.",
    color=0xe74c3c
)

MODULE_PREFIX = "Modules"

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
        self.started = False

    # Loading modules
    async def on_ready(self):
        if self.started:
            logger.success(f"Relogged in as \"{self.user}\" ({self.user.id})")
        else:
            logger.success(f"Logged in as \"{self.user}\" ({self.user.id})")
            self.started = True

    def load_modules(self):
        logger.info("Loading modules...")
        
        modules_dirs = ["modules"]

        for directory in modules_dirs:
            if not os.path.exists(directory):
                logger.warning(f"Directory '{directory}' not found, skipping.")
                continue

            for filename in os.listdir(directory):
                if filename.endswith(".py") and not filename.startswith("_"):
                    if filename.startswith("dev_") and not DEVELOPER_MODE:
                        continue
                    
                    self.load_single_module(directory, filename)
            
        logger.info("Finished loading modules.", MODULE_PREFIX)
        logger.info(f"Total modules loaded: {len(self.extensions)}", MODULE_PREFIX)

    def load_single_module(self, directory: str, filename: str):
        module_path = f"{directory}.{filename[:-3]}"
        try:
            self.load_extension(module_path)
            prefix = "Development module" if filename.startswith("dev_") else "Module"
            logger.success(f"Loaded {prefix}: {filename}", MODULE_PREFIX)
        except Exception as e:
            logger.error(f"Error loading module {filename}: {e}", MODULE_PREFIX)

async def load_configs():
    await MAIN_CONFIG.validate()

async def main():
    global DEVELOPER_MODE

    await load_configs()

    if args.dev:
        logger.info("Running in developer mode. Developer modules will be loaded.")
        DEVELOPER_MODE = True

    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is not set in the environment variables. (.env)")
        return

    bot = Bot()
    bot.load_modules()
    
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await bot.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Dolfirobots Network Discord Bot',
        description='A Discord bot for Dolfirobots Network Discord server'
    )

    parser.add_argument("-l", "--log", "--loglevel", type=str, default="INFO")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--setup", action="store_true")

    args = parser.parse_args()
    
    CURRENT_LOG_LEVEL = LogLevel.from_string(args.log)

    if args.setup:
        logger.info("Starting setup wizard...")
        dot_env = pathlib.Path(".env")
        
        if dot_env.exists():
            logger.warning("An .env file already exists!")
            confirm = input("Do you want to modify the existing .env file? (y/n): ").lower()
            if confirm.lower() != 'y':
                logger.info("Setup cancelled.")
                exit()

        current_tokens = {
            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN", "")
        }

        new_token = getpass.getpass(f"Enter Main DISCORD_TOKEN [{current_tokens['DISCORD_TOKEN'][:11]}...]: ").strip()
        if new_token: current_tokens["DISCORD_TOKEN"] = new_token

        try:
            with open(dot_env, "w", encoding="utf-8") as f:
                for key, value in current_tokens.items():
                    f.write(f"{key}={value}\n")
            logger.success("Setup completed! Please restart the bot without --setup.")
        except Exception as e:
            logger.error(f"Failed to write .env file: {e}")
        exit()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass