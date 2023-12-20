from disnake.ext.commands import NotOwner
from enum import Enum


class EmbedColor(Enum):
    INFO = 0x000080  # blued
    ERROR = 0xff0010  # red
    SUCCESS = 0x00ff00  # green
    WARNING = 0xff8000  # orange

# def is_admin(ctx):
#     """
#     Simple check to see if the user invoking a command contains the elder role
#     Parameters
#     ----------
#     ctx : discord.ext.commands.Context
#         Represents the context in which a command is being invoked under.
#     Returns
#     -------
#     bool:
#         True or False if user is an elder
#     """
#     for role in ctx.author.roles:
#         if role.id == OWNER:
#             return True
#     return False


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
    print(dir(ctx))
    return NotOwner
    # if ctx.author.id == OWNER:
    #     return True
    # else:
    #     raise NotOwner("Not owner")


# def is_leader(ctx):
#     if ctx.author.id == OWNER:
#         return True
#     for role in ctx.author.roles:
#         if role.id == LEADERS:
#             return True
#     return False