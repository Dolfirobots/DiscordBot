import time
from disnake.ext import commands
import disnake
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger
from utils import ErrorEmbed, SuccessEmbed, PermissionEmbed
from ticket import Ticket, TicketState, TicketCategory, CREATE_EMBED, init_db
from main import MAIN_CONFIG

PREFIX = "Ticket Command"

class TicketDropdown(disnake.ui.Select):
    def __init__(self):
        options = [
            disnake.SelectOption(label="General Support", description="General questions about the server or our services.", emoji="💬", value="general"),
            disnake.SelectOption(label="Report a Player", description="Report a player for breaking the rules.", emoji="🚨", value="report"),
            disnake.SelectOption(label="Team Application", description="Apply to join our team.", emoji="📝", value="team_apply"),
            disnake.SelectOption(label="Bug Report", description="Report a bug in the game or website.", emoji="🐛", value="bug"),
        ]
        super().__init__(
            placeholder="Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_persistent"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        ns_time = time.time_ns()
        await inter.response.defer(ephemeral=True)
        
        # Reset the selection
        try:
            await inter.edit_original_message(view=self.view)
        except Exception as e:
            logger.critical(f"There was an error by resetting the user selection: {e}", PREFIX)
            await inter.followup.send(
                embed=ErrorEmbed(
                    "There was an error by resetting the user selection",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True
            )

        try:
            category_key = self.values[0]
            category_obj = TicketCategory.from_str(category_key)

            ticket = Ticket(
                bot=inter.bot,
                guild_id=inter.guild_id,
                category_id=inter.channel.category_id,
                user_id=inter.author.id,
                state=TicketState.OPEN,
                category=category_obj
            )
            channel = await ticket.create()

            logger.info(f"#{ticket.id}: New ticket created from @{inter.author.name} for {category_obj.get_title()}.", PREFIX)
            
            await inter.followup.send(
                embed=SuccessEmbed(
                    f"Your ticket has been created at: {channel.mention}",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True,
                delete_after=10
            )
        except Exception as e:
            logger.error(f"Error during ticket creation: {e}", PREFIX)
            await inter.followup.send(
                embed=ErrorEmbed(
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True
            )

class TicketView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

class TicketModule(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.slash_command(description="Sends create ticket message")
    async def setup_ticket(self, inter: disnake.ApplicationCommandInteraction):
        ns_time = time.time_ns()
        await inter.response.defer(ephemeral=True)

        config_data = await MAIN_CONFIG.load_json()
        admin_roles = config_data.get("roles", {}).get("admin", [])

        user_role_ids = [role.id for role in inter.author.roles]
        is_admin = any(role_id in admin_roles for role_id in user_role_ids)

        if not is_admin:
            await inter.followup.send(
                embed=PermissionEmbed(
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True
            )
            return

        try:
            embed = await CREATE_EMBED(inter) 
            await inter.channel.send(embed=embed, view=TicketView())

            await inter.followup.send(
                embed=SuccessEmbed(
                    "The ticket create message was successfully send in this channel!",
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error while sending ticket create message: {e}", PREFIX)
            await inter.followup.send(
                embed=ErrorEmbed(
                    service="Tickets",
                    time=time.time_ns() - ns_time
                ),
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketView())
        await init_db()

def setup(bot: commands.Bot):
    bot.add_cog(TicketModule(bot))