from typing import TYPE_CHECKING
from enum import Enum

from disnake.ext.commands import NotOwner
import disnake

if TYPE_CHECKING:
    from bot import BotClient


class EmbedColor(Enum):
    INFO = 0x000080  # blued
    ERROR = 0xff0010  # red
    SUCCESS = 0x00ff00  # green
    WARNING = 0xff8000  # orange


def is_admin(ctx):
    """
    Simple check to see if the user invoking a command contains the elder role
    Parameters
    ----------
    ctx : discord.ext.commands.Context
        Represents the context in which a command is being invoked under.
    Returns
    -------
    bool:
        True or False if user is an elder
    """
    admin_role = ctx.bot.settings.get_role("admin")
    for role in ctx.author.roles:
        if role.id == admin_role:
            return True
    return False


def is_owner(ctx):
    """
    Simple check to see if the user invoking a command is the owner
    Parameters
    ----------
    ctx : discord.ext.commands.Context
        Represents the context in which a command is being invoked under.
    Returns
    -------
    bool:
        True or False if user is an elder
    """
    if ctx.author.id == ctx.bot.settings.owner:
        return True
    else:
        raise NotOwner("Not owner")


def to_title(inter: disnake.ApplicationCommandInteraction, panel_name: str
             ) -> str:
    """Function acts as a parameter function for  Happy.py"""
    return panel_name.title()


def get_role(bot: "BotClient", role_name: str | int) -> disnake.Role:
    guild = bot.get_guild(bot.settings.guild)

    if isinstance(role_name, str):
        return guild.get_role(bot.settings.get_role(role_name))
    else:
        return guild.get_role(role_name)


async def kick_user(bot: "BotClient", member: disnake.Member) -> None:
    reason = "Member took too long to interact with introduction channel"
    await member.kick(reason=reason)

    mod_log = bot.get_channel(
        bot.settings.get_channel("mod-log"))

    await bot.inter_send(
        mod_log,
        title=f"Member has been kicked by `HogRider`",
        panel=f"**Reason:**\n{reason}",
        author=member,
        color=EmbedColor.ERROR
    )
