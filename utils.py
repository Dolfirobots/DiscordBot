import disnake
from datetime import datetime

async def check_message_exists(channel: disnake.TextChannel, message_id: int):
    try:
        await channel.fetch_message(message_id)
        return True
    except disnake.NotFound:
        return False
    except disnake.Forbidden:
        return False
    except disnake.HTTPException:
        return False

def ErrorEmbed(description: str = None, title: str = None, service: str = None, time: int = None):
    embed = disnake.Embed(
        title="❌ Error" if title is None else title,
        description="An unexpected error occurred. Please try again later." if description is None else description,
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    return FooterEmbed(embed=embed, service=service, time=time, text="Please open a Ticket or contact an Admin if this is an important error")

def PermissionEmbed(description: str = None, title: str = None, service: str = None, time: int = None):
    embed = disnake.Embed(
        title="🚫 Permission Denied" if title is None else title,
        description="You do not have the required permissions to use this." if description is None else description,
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    return FooterEmbed(embed=embed, service=service, time=time, text="If this is an error please open a Ticket or contact an Admin")

def SuccessEmbed(description: str = None, title: str = None, service: str = None, time: int = None):
    embed = disnake.Embed(
        title="✅ Success" if title is None else title,
        description="The action was completed successfully." if description is None else description,
        color=0x2ecc71,
        timestamp=datetime.now()
    )
    return FooterEmbed(embed=embed, service=service, time=time)

def FooterEmbed(embed: disnake.Embed, time: int = None, service: str = None, text: str = None, icon_file = None, icon_url = None) -> disnake.Embed:
    footer = "Dolfirobots Networks"
    if service:
        footer += f" • {service}"
    if time is not None:
        footer += f" • {round(time / 1_000_000)}ms"
    if text:
        footer = f"{text}\n{footer}"

    if icon_file:
        return embed.set_footer(text=footer, icon_file=icon_file)
    elif icon_url:
        return embed.set_footer(text=footer, icon_url=icon_url)
    else:
        return embed.set_footer(text=footer)