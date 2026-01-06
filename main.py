import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

import asyncio
import pathlib
import disnake
import os
import argparse
import getpass

from disnake.ext import commands
from dotenv import load_dotenv

from logger import logger, LogLevel
from config import Config

# Load config from .env file
load_dotenv()

# Project variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TICKET_DISCORD_TOKEN = os.getenv("TICKET_DISCORD_TOKEN")

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
MAIN_CONFIG = Config("config.json")

TICKET_MODE = False
DUAL_MODE = False
DEVELOPER_MODE = False

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

    # Loading modules
    async def on_ready(self):
        if TICKET_MODE:
            logger.success(f"Ticket Bot logged in as \"{self.user}\" ({self.user.id})")
        else:
            logger.success(f"Logged in as \"{self.user}\" ({self.user.id})")

    def load_modules(self):
        logger.info("Loading modules...")
        
        modules_dirs = []

        if TICKET_MODE or DUAL_MODE:
            modules_dirs.append("ticket_modules")
        
        if not TICKET_MODE:
            modules_dirs.append("modules")

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
    try:
        await MAIN_CONFIG.validate()
    except Exception:
        pass

async def main():
    global DISCORD_TOKEN, TICKET_MODE, DUAL_MODE, DEVELOPER_MODE

    await load_configs()

    if args.dual:
        logger.info("Starting Bot in dual mode...")
        DUAL_MODE = True

    if args.ticket:
        if DUAL_MODE:
            logger.warning("The Main has the Ticket Bot features, no new Bot must start!")
        else:
            if not TICKET_DISCORD_TOKEN:
                logger.critical("TICKET_DISCORD_TOKEN is not set in the environment variables. (.env)")
                return
            logger.info("Starting Ticket Bot...")
            TICKET_MODE = True
            DISCORD_TOKEN = TICKET_DISCORD_TOKEN

    if args.dev:
        logger.info("Running in developer mode. Developer modules will be loaded.")
        DEVELOPER_MODE = True

    if not DISCORD_TOKEN and not TICKET_MODE:
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
    parser.add_argument("-t", "--ticket", action="store_true")
    parser.add_argument("-d", "--dual", action="store_true")
    parser.add_argument("--setup", action="store_true")

    args = parser.parse_args()
    
    CURRENT_LOG_LEVEL = LogLevel.from_string(args.log)

    if args.setup:
        logger.info("Starting setup wizard...")
        dot_env = pathlib.Path(".env")
        
        if dot_env.exists():
            logger.warning("An .env file already exists!")
            confirm = input("Do you want to modify the existing .env file? (y/n): ").lower()
            if confirm != 'y':
                logger.info("Setup cancelled.")
                exit()

        current_tokens = {
            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN", ""),
            "TICKET_DISCORD_TOKEN": os.getenv("TICKET_DISCORD_TOKEN", "")
        }

        logger.info("--- Token Configuration ---")
        logger.info("1) Main Discord Token")
        logger.info("2) Ticket Discord Token")
        logger.info("3) Both")
        logger.info("4) Cancel")
        choice = input("Choice (1-4): ")

        if choice == "4": exit()

        if choice in ["1", "3"]:
            new_main = getpass.getpass(f"Enter Main DISCORD_TOKEN [{current_tokens['DISCORD_TOKEN'][:11]}...]: ").strip()
            if new_main: current_tokens["DISCORD_TOKEN"] = new_main

        if choice in ["2", "3"]:
            new_ticket = getpass.getpass(f"Enter TICKET_DISCORD_TOKEN [{current_tokens['TICKET_DISCORD_TOKEN'][:11]}...]: ").strip()
            if new_ticket: current_tokens["TICKET_DISCORD_TOKEN"] = new_ticket

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