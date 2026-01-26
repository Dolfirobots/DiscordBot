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
from ticket import get_create_embed, fetch_ticket_by_channel, Ticket, TicketState, send_manage_embed


async def check_permissions(ctx: commands.Context | disnake.MessageInteraction, ticket: Ticket):
    user_role_ids = [role.id for role in ctx.author.roles]
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

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel.id)
        if not ticket:
            return await inter.followup.send(
                embed=ErrorEmbed(
                    "This channel is not associated with a ticket!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True,
                delete_after=5
            )

        if not await check_permissions(inter, ticket):
            return await inter.followup.send(
                embed=PermissionEmbed(
                    time=time.time_ns() - ns_time,
                    service="Tickets"
                ),
                ephemeral=True,
                delete_after=5
            )
        
        if ticket.state == TicketState.CLOSED:
            return await inter.followup.send(
                embed=ErrorEmbed(
                    "Ticket is already closed!",
                     time=time.time_ns() - ns_time,
                     service="Tickets"
                ),
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

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel.id)
        if not ticket:
            return await inter.send(
                embed=ErrorEmbed(
                    "This channel is not associated with a ticket!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                delete_after=5
            )

        # Check permissions
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
        embed.add_field(name="📶 Status", value="`🟢 OPEN`", inline=True)

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
        return None

    @disnake.ui.button(label="Delete Ticket", style=disnake.ButtonStyle.grey, custom_id="delete_ticket_button", emoji="⚠️")
    async def delete_ticket(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        ns_time = time.time_ns()
        await inter.response.defer()

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(inter.bot, inter.channel.id)
        if not ticket:
            return await inter.followup.send(
                embed=ErrorEmbed(
                    "This channel is not associated with a ticket!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                delete_after=5
            )

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
        return None


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
            return None

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(self.bot, message.channel.id)
        if not ticket:
            return None

        log_channel_id = (await MAIN_CONFIG.load_json()).get("ticket", {}).get("log_channel")
        log_channel = self.bot.get_channel(log_channel_id) or message.channel

        embed = disnake.Embed(
            title="❌ Message Deleted",
            color=disnake.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="User (Editor)", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Ticket", value=f"<#{ticket.channel_id}> (ID: `#{ticket.id}`)", inline=False)

        content = message.content if message.content else "*No text content (likely an image or embed)*"
        if len(content) > 1024:
            content = content[:1020] + "..."

        embed.add_field(name="Content", value=f"```\n{content}\n```", inline=False)
        embed = FooterEmbed(
            embed=embed,
            icon_url=self.bot.user.display_avatar.url,
            service="Tickets",
            time=time.time_ns() - ns_time
        )
        await log_channel.send(embed=embed)
        return None

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        ns_time = time.time_ns()
        if before.author.bot or before.content == after.content:
            return None

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(self.bot, before.channel.id)
        if not ticket:
            return None

        log_channel_id = (await MAIN_CONFIG.load_json()).get("ticket", {}).get("log_channel")
        log_channel = self.bot.get_channel(log_channel_id)

        if log_channel:
            embed = disnake.Embed(
                title="✏️ Message Edited",
                color=disnake.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{after.author.mention} (`{after.author.id}`)", inline=False)
            embed.add_field(name="Ticket", value=f"<#{ticket.channel_id}> (ID: `#{ticket.id}`)", inline=False)

            content_before = before.content if before.content else "*No text content (likely an image or embed)*"
            if len(content_before) > 1024:
                content_before = content_before[:1020] + "..."

            content_after = after.content if after.content else "*No text content (likely an image or embed)*"
            if len(content_after) > 1024:
                content_after = content_after[:1020] + "..."

            embed.add_field(name="Before", value=f"```\n{content_before}\n```", inline=False)
            embed.add_field(name="After", value=f"```\n{content_after}\n```", inline=False)
            embed = FooterEmbed(
                embed=embed,
                icon_url=self.bot.user.display_avatar.url,
                service="Tickets",
                time=time.time_ns() - ns_time
            )
            await log_channel.send(embed=embed)
        return None

    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_command(self, ctx: commands.Context):
        ns_time = time.time_ns()

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(self.bot, ctx.channel.id)
        if not ticket:
            return await ctx.send(
                embed=ErrorEmbed(
                    "This channel is not associated with a ticket!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                delete_after=5
            )
        # Permission check
        if not await check_permissions(ctx, ticket):
            return await ctx.send(embed=PermissionEmbed(
                time=time.time_ns() - ns_time,
                service="Tickets",
            ))

        await ctx.message.delete()
        return await ctx.send(
            embed=ErrorEmbed(
                "Usage: `!ticket reload`",
                time=time.time_ns() - ns_time,
                service="Tickets"
            ),
            delete_after=5
        )

    @ticket_command.command(name="reload")
    async def ticket_reload(self, ctx: commands.Context):
        ns_time = time.time_ns()

        # Checking if the channel is associated with a ticket
        ticket = await fetch_ticket_by_channel(ctx.bot, ctx.channel.id)
        if not ticket:
            return await ctx.send(
                embed=ErrorEmbed(
                    "This channel is not associated with a ticket!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                )
            )

        # No permission
        if not await check_permissions(ctx, ticket):
            return await ctx.send(embed=PermissionEmbed(
                time=time.time_ns() - ns_time,
                service="Tickets",
            ))

        await ctx.message.delete()
        current_view = ManageView() if ticket.state == TicketState.OPEN else ClosedManageView()
        try:
            # The message exist, so just update the view
            message = await ctx.channel.fetch_message(ticket.manage_id)
            await message.edit(view=current_view)

            await ctx.send(
                embed=SuccessEmbed(
                    "Ticket management interface has been refreshed!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                delete_after=5
            )
        except (disnake.NotFound, disnake.Forbidden):
            # The message doesn't exist
            message = await send_manage_embed(ticket, ns_time, ctx.channel)
            # Update manage message id in the database
            await ticket.update_manage_msg(message.id)

            await ctx.send(
                embed=SuccessEmbed(
                    "Ticket management interface has been resent!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                delete_after=5
            )

def setup(bot):
    bot.add_cog(ManageModule(bot))