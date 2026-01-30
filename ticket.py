from enum import Enum
import disnake
import aiosqlite
from disnake.ext import commands
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from main import MAIN_CONFIG
from utils import FooterEmbed
from logger import logger
from modules import manage_module

PREFIX = "Database"
DATABASE = "assets/tickets.db"

class TicketState:
    OPEN = 1
    CLOSED = 0

class TicketCategory(Enum):
    GENERAL = ("General Support", [1461393582312128656])
    REPORT = ("Report Player", [1461393648582135829])
    TEAM_APPLY = ("Team Application", [1461393793785008259])
    BUG = ("Bug Report", [1461393834264105181])

    def __init__(self, title, roles):
        self._title = title
        self._roles = roles

    def get_title(self) -> str:
        return self._title

    def get_roles(self) -> list[int]:
        return self._roles

    @classmethod
    def from_str(cls, name: str):
        try:
            return cls[name.upper()]
        except KeyError:
            return cls.GENERAL

class Ticket:
    def __init__(self, bot: commands.Bot, guild_id: int, category_id: int, user_id: int, category: TicketCategory, ticket_id: int = None, state: int = TicketState.OPEN, channel_id: int = None, manage_id: int = None, created_at: int = None):
        self.bot = bot
        self.id = ticket_id

        self.guild_id = guild_id
        self.category_id = category_id
        self.channel_id = channel_id
        self.manage_id = manage_id

        self.category = category
        self.user_id = user_id
        self.state = state
        self.created_at = created_at

    async def create(self) -> disnake.TextChannel:
        ns_time = time.time_ns()

        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            guild = await self.bot.fetch_guild(self.guild_id)

        self.created_at = time.time()

        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "INSERT INTO tickets (guild, category_id, user_id, state, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.guild_id, self.category_id, self.user_id, self.state, self.category.name, self.created_at)
            )
            self.id = cursor.lastrowid
            await db.commit()

        channel = await self.update_channel()

        manage_message = await send_manage_embed(self, ns_time, channel)

        self.manage_id = manage_message.id
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE tickets SET manage_id = ? WHERE ticket_id = ?", (self.manage_id, self.id))
            await db.commit()

        logger.success(f"Created new ticket: ID: {self.id}, User ID: {self.user_id}, Category: {self.category.get_title()}", PREFIX)
        return channel
    
    async def update_channel(self) -> disnake.TextChannel:
        guild = self.bot.get_guild(self.guild_id) or await self.bot.fetch_guild(self.guild_id)
        
        prefix = "🟢" if self.state == TicketState.OPEN else "🔴"
        channel_name = f"{prefix}｜ticket-{self.id:04d}"
        
        channel = None
        if self.channel_id:
            channel = guild.get_channel(self.channel_id)
            if not channel:
                try:
                    channel = await guild.fetch_channel(self.channel_id)
                except disnake.NotFound:
                    channel = None

        if channel is None:
            category = self.bot.get_channel(self.category_id)
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category
            )
            self.channel_id = channel.id
            
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE tickets SET channel_id = ? WHERE ticket_id = ?", (self.channel_id, self.id))
                await db.commit()
        else:
            if channel.name != channel_name:
                await channel.edit(name=channel_name)

        await self.reload_permissions()
        return channel
    
    async def update_manage_msg(self, id: int):
        self.manage_id = id
        async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE tickets SET manage_id = ? WHERE ticket_id = ?", (self.manage_id, self.id))
                await db.commit()

    async def reload_permissions(self) -> disnake.TextChannel | None:
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            guild = await self.bot.fetch_guild(self.guild_id)
        
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return None
        
        user = await self.bot.get_or_fetch_user(self.user_id)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            user: disnake.PermissionOverwrite(
                view_channel=True, 
                send_messages=(self.state == TicketState.OPEN),
                attach_files=(self.state == TicketState.OPEN),
                read_message_history=True,
                manage_messages=False
            ),
            guild.me: disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True
            )
        }

        category_role_ids = self.category.get_roles()
        
        for role_id in category_role_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = disnake.PermissionOverwrite(
                    view_channel=True, 
                    send_messages=(self.state == TicketState.OPEN),
                    attach_files=(self.state == TicketState.OPEN), 
                    read_message_history=True,
                    manage_messages=False,
                )

        await channel.edit(overwrites=overwrites)
        return channel
    
    async def update_state(self, state: TicketState):
        self.state = state
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE tickets SET state = ? WHERE ticket_id = ?", (self.state, self.id))
            await db.commit()

        await self.update_channel()

    async def get_user(self):
        return await self.bot.get_or_fetch_user(self.user_id)

    async def delete(self):
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM tickets WHERE ticket_id = ?", (self.id,))
            await db.commit()
        
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            try:
                await channel.delete()
            except disnake.NotFound:
                pass

    async def update(self):
        ticket = await fetch_ticket(self.bot, self.id)

        if ticket:
            self.guild_id = ticket.guild_id
            self.category_id = ticket.category_id
            self.channel_id = ticket.channel_id
            self.manage_id = ticket.manage_id

            self.category = ticket.category
            self.user_id = ticket.user_id
            self.state = ticket.state
        await self.update_channel()


async def fetch_ticket(bot: commands.Bot, ticket_id: int) -> Ticket:
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Ticket(
                    bot=bot,
                    ticket_id=row["ticket_id"],

                    guild_id=row["guild"],
                    category_id=row["category_id"],
                    channel_id=row["channel_id"],
                    manage_id=row["manage_id"],
                    
                    category=TicketCategory.from_str(row["category"]),
                    user_id=row["user_id"],
                    state=row["state"],
                    created_at=row["created_at"]
                )
    return None

async def fetch_ticket_by_channel(bot: commands.Bot, channel_id: int) -> Ticket:
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Ticket(
                    bot=bot,
                    ticket_id=row["ticket_id"],

                    guild_id=row["guild"],
                    category_id=row["category_id"],
                    channel_id=row["channel_id"],
                    manage_id=row["manage_id"],
                    
                    category=TicketCategory.from_str(row["category"]),
                    user_id=row["user_id"],
                    state=row["state"],
                    created_at=row["created_at"]
                )
    return None

async def fetch_all_tickets(bot: commands.Bot) -> list[Ticket]:
    tickets = []
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets") as cursor:
            async for row in cursor:
                tickets.append(Ticket(
                    bot=bot,
                    ticket_id=row["ticket_id"],

                    guild_id=row["guild"],
                    category_id=row["category_id"],
                    channel_id=row["channel_id"],
                    manage_id=row["manage_id"],

                    category=TicketCategory.from_str(row["category"]),
                    user_id=row["user_id"],
                    state=row["state"],
                    created_at=row["created_at"]
                ))
    return tickets

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                         
                guild INTEGER,
                category_id INTEGER,
                channel_id INTEGER,
                manage_id INTEGER,

                category TEXT,
                user_id INTEGER,
                state INTEGER,
                created_at TIMESTAMP
            )
        """)
        await db.commit()

async def send_manage_embed(ticket: Ticket, ns_time: int, channel: disnake.TextChannel) -> disnake.Message:
    embed = disnake.Embed(
        title="🎫 Ticket Support",
        description=(
            f"Hello <@{ticket.user_id}>, welcome to your ticket.\n"
            "Our staff team has been notified and will assist you shortly.\n\n"
            f"**Selected Category:** *{ticket.category.get_title()}*"
        ),
        color=0x2b2d31
    )

    embed = FooterEmbed(
        embed=embed,
        service="Tickets",
        time=time.time_ns() - ns_time
    )
    admin_pings = " ".join([f"<@&{role_id}>" for role_id in ticket.category.get_roles()])

    return await channel.send(
        content=f"<@{ticket.user_id}> {admin_pings}",
        embed=embed,
        view=manage_module.ManageView() if ticket.state == TicketState.OPEN else manage_module.ClosedManageView()
    )

async def get_create_embed(bot: commands.Bot) -> disnake.Embed:
    data = await MAIN_CONFIG.load_json()
    icon = data.get("emojis", {}).get("ticket", "🎫")

    embed = disnake.Embed(
        description=(
            f"## {icon} Ticket System\n"
            "Welcome to our **Official Support System**. \n"
            "If you need help, want to report a player, or have a general inquiry, "
            "you are in the right place!\n\n"
            "**How it works:**\n"
            " - Choose the appropriate category from the dropdown menu below.\n"
            " - Click the 'Create Ticket' button to open your ticket.\n"
            " - A private channel will be created for you and the staff.\n"
            " - Describe your issue in detail to receive faster help.\n\n"
            "*Please be patient, our team will be with you as soon as possible.*"
        ),
        color=0x2b2d31
    )
    
    embed.set_image(url="https://i.imgur.com/i6YJCZW.png")
    
    embed = FooterEmbed(
        embed=embed,
        service="Tickets",
        icon_url=bot.user.display_avatar.url,
    )
    return embed