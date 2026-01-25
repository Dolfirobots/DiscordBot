import asyncio
from disnake.ext import commands
import disnake
from datetime import datetime
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import MAIN_CONFIG
from logger import logger
from utils import ErrorEmbed, PermissionEmbed, SuccessEmbed, FooterEmbed
from ticket import CREATE_EMBED, fetch_ticket_by_channel, Ticket, TicketState

async def check_permissions(inter: disnake.MessageInteraction, ticket: Ticket):
    user_role_ids = [role.id for role in inter.author.roles]
    config_data = await MAIN_CONFIG.load_json()
    admin_roles = config_data.get("roles", {}).get("admin", [])
    is_admin = any(role_id in user_role_ids for role_id in admin_roles)
    is_staff = any(role_id in user_role_ids for role_id in ticket.category.get_roles())
    return is_admin or is_staff

class ManageView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Close Ticket", style=disnake.ButtonStyle.red, custom_id="close_ticket_button", emoji="🔒")
    async def close_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        ns_time = time.time_ns()
        await inter.response.defer()

        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel_id)
        if not ticket:
            return await inter.followup.send(
                embed=ErrorEmbed("No active ticket found!",
                                 time=time.time_ns() - ns_time,
                                 service="Tickets"),
                ephemeral=True)

        if not await check_permissions(inter, ticket):
            return await inter.followup.send(
                    embed=PermissionEmbed(
                        time=time.time_ns() - ns_time,
                        service="Tickets"
                    ),
                    ephemeral=True
                )
        
        if ticket.state == TicketState.CLOSED:
            return await inter.followup.send(
                embed=ErrorEmbed("Ticket is already closed!",
                                 time=time.time_ns() - ns_time,
                                 service="Tickets"),
                ephemeral=True)
        
        await ticket.update_state(TicketState.CLOSED)
        logger.info(f"Closed ticket by @{inter.author.name}", f"Ticket #{ticket.id}")

        duration_str = "Unknown"
        if ticket.created_at:
            start_time = datetime.fromtimestamp(ticket.created_at) if isinstance(ticket.created_at, (int, float)) else ticket.created_at
            delta = datetime.now() - start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m"

        embed = disnake.Embed(
            title="🔒 Ticket Closed",
            description=(
                "This ticket has been marked as **closed**.\n"
                "No one can send messages here now"
            ),
            color=0xe74c3c,
            timestamp=datetime.now()
        )

        embed.add_field(name="👤 Closed by", value=inter.author.mention, inline=True)
        embed.add_field(name="📂 Category", value=f"`{ticket.category.get_title()}`", inline=True)
        embed.add_field(name="🆔 Ticket ID", value=f"`#{ticket.id}`", inline=True)
        embed.add_field(name="⏱️ Opened for", value=f"`{duration_str}`", inline=True)
        embed.add_field(name="👤 Owner", value=f"<@{ticket.user_id}>", inline=True)

        embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed = FooterEmbed(
            embed=embed,
            icon_url=inter.bot.user.display_avatar.url,
            time=time.time_ns() - ns_time,
            service="Tickets"
        )

        await inter.channel.send(embed=embed)

        try:
            message = await inter.channel.fetch_message(ticket.manage_id)
            await message.edit(view=ClosedManageView())
        except disnake.NotFound:
            logger.error(f"Manage message {ticket.manage_id} not found.")

class ClosedManageView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Open Ticket", style=disnake.ButtonStyle.green, custom_id="open_ticket_button", emoji="🔓")
    async def open_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        ns_time = time.time_ns()
        await inter.response.defer()
        
        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel_id)
        if ticket:
            if not await check_permissions(inter, ticket):
                return await inter.followup.send(
                    embed=PermissionEmbed(
                        time=time.time_ns() - ns_time,
                        service="Tickets"
                    ),
                    ephemeral=True
                )

            await ticket.update_state(TicketState.OPEN)
            
            embed = disnake.Embed(
                title="🔓 Ticket Re-Opened",
                description=(
                    f"This ticket has been **re-opened** by {inter.author.mention}.\n"
                    "The support team has been notified and will be with you shortly."
                ),
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )

            embed.add_field(name="📂 Category", value=f"`{ticket.category.get_title()}`", inline=True)
            embed.add_field(name="🆔 Ticket ID", value=f"`#{ticket.id}`", inline=True)
            embed.add_field(name="📶 Status", value="`🟢 ACTIVE / OPEN`", inline=True)

            staff_mentions = " ".join([f"<@&{role_id}>" for role_id in ticket.category.get_roles()])
            if staff_mentions:
                embed.add_field(name="🛡️ Staff Notified", value=staff_mentions, inline=False)

            embed.set_thumbnail(url=inter.author.display_avatar.url)
            embed = FooterEmbed(
                embed=embed,
                icon_url=inter.bot.user.display_avatar.url,
                time=time.time_ns() - ns_time,
                service="Tickets"
            )

            await inter.channel.send(embed=embed)

            try:
                message = await inter.channel.fetch_message(ticket.manage_id)
                await message.edit(view=ManageView())
            except disnake.NotFound:
                logger.error(f"Manage message {ticket.manage_id} not found.")

    @disnake.ui.button(label="Delete Ticket", style=disnake.ButtonStyle.grey, custom_id="delete_ticket_button", emoji="⚠️")
    async def delete_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        ns_time = time.time_ns()
        await inter.response.defer()

        data = await MAIN_CONFIG.load_json()
        tickets_category_id = data.get("ticket", {}).get("ticket_category")

        if inter.channel.category_id != tickets_category_id:
            return

        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel_id)
        if ticket:
            if not await check_permissions(inter, ticket):
                return await inter.followup.send(
                    embed=PermissionEmbed(
                        time=time.time_ns() - ns_time,
                        service="Tickets"
                    ),
                    ephemeral=True
                )

            delete_embed = disnake.Embed(
                title="⚠️ Ticket Deletion",
                description="This channel will be deleted in **a few seconds**.",
                color=disnake.Color.orange()
            )

            delete_embed = FooterEmbed(
                embed=delete_embed,
                icon_url=inter.bot.user.display_avatar.url,
                time=time.time_ns() - ns_time,
                service="Tickets"
            )
            await inter.channel.send(embed=delete_embed)

            await asyncio.sleep(2)
            await ticket.delete()
            logger.info(f"Deleted ticket by @{inter.author.name}", f"Ticket #{ticket.id}")

class ManageModule(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ManageView())
        self.bot.add_view(ClosedManageView())

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        ns_time = time.time_ns()
        if message.author.bot:
            return

        data = await MAIN_CONFIG.load_json()
        tickets_category_id = data.get("ticket", {}).get("ticket_category")

        if message.channel.category_id != tickets_category_id:
            return

        ticket = await fetch_ticket_by_channel(self.bot, message.channel)
        if ticket:
            log_channel_id = data.get("ticket", {}).get("log_channel")
            log_channel = self.bot.get_channel(log_channel_id) or message.channel

            embed = disnake.Embed(
                title="❌ Message Deleted in Ticket",
                description=f"A message was deleted in {message.channel.mention}",
                color=disnake.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
            embed.add_field(name="Ticket ID", value=f"`#{ticket.id}`", inline=True)
            
            content = message.content if message.content else "*No text content (likely an image or embed)*"
            if len(content) > 1024:
                content = content[:1020] + "..."
                
            embed.add_field(name="Content", value=content, inline=False)
            embed = FooterEmbed(
                embed=embed,
                text=f"Channel: #{message.channel.name}",
                icon_url=self.bot.user.display_avatar.url,
                service="Tickets",
                time=time.time_ns() - ns_time
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        ns_time = time.time_ns()
        if before.author.bot or before.content == after.content:
            return
        
        data = await MAIN_CONFIG.load_json()
        tickets_category_id = data.get("ticket", {}).get("ticket_category")

        if before.channel.category_id != tickets_category_id:
            return

        ticket = await fetch_ticket_by_channel(self.bot, before.channel.id)
        if ticket:
            log_channel_id = (await MAIN_CONFIG.load_json()).get("ticket", {}).get("log_channel")
            log_channel = self.bot.get_channel(log_channel_id)
            
            if log_channel:
                embed = disnake.Embed(
                    title="📝 Message Edited in Ticket",
                    color=disnake.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="User", value=before.author.mention, inline=True)
                embed.add_field(name="Before", value=before.content, inline=False)
                embed.add_field(name="After", value=after.content, inline=False)
                embed = FooterEmbed(
                    embed=embed,
                    icon_url=self.bot.user.display_avatar.url,
                    service="Tickets",
                    time=time.time_ns() - ns_time
                )
                await log_channel.send(embed=embed)

    @commands.slash_command(description="Updates the ticket management message in this channel.")
    async def update_ticket(self, inter: disnake.ApplicationCommandInteraction):
        ns_time = time.time_ns()
        await inter.response.defer(ephemeral=True)

        data = await MAIN_CONFIG.load_json()
        tickets_category_id = data.get("ticket", {}).get("ticket_category")

        if inter.channel.category_id != tickets_category_id:
            return

        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel_id)
        if not ticket:
            return await inter.followup.send(
                embed=ErrorEmbed(
                    "This channel is not a valid ticket channel!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ), 
                ephemeral=True
            )

        if not await check_permissions(inter, ticket):
            return await inter.followup.send(embed=PermissionEmbed(), ephemeral=True)
        
        current_view = ManageView() if ticket.state == TicketState.OPEN else ClosedManageView()
        try:
            message = await inter.channel.fetch_message(ticket.manage_id)
            await message.edit(view=current_view)
            await inter.followup.send(
                embed=SuccessEmbed(
                    "Ticket management interface has been refreshed!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ), 
                ephemeral=True,
                delete_after=5
            )
        except (disnake.NotFound, disnake.Forbidden):
            embed = await CREATE_EMBED(inter)
            message = await inter.channel.send(embed=embed, view=current_view)

            await ticket.update_manage_msg(message.id)

            await inter.followup.send(
                embed=SuccessEmbed(
                    "Ticket management interface has been resended!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ), 
                ephemeral=True,
                delete_after=5
            )

def setup(bot):
    bot.add_cog(ManageModule(bot))