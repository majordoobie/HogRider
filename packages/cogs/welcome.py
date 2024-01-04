from logging import getLogger

import disnake.abc
from disnake.abc import GuildChannel, PrivateChannel
from disnake.ext import commands
from disnake import ApplicationCommandInteraction, Thread

from bot import BotClient
from packages.utils.utils import is_admin
from packages.config import guild_ids, BotMode
from packages.views.welcome_views import WelcomeView

WELCOME_MESSAGE = (
    "We're glad to have you! We're here to help you do the things you want "
    "to do with the Clash API. While we can "
    "provide some language specific guidance, **we are not a learn to code "
    "server**. There are plenty of resources out there for that. But if you "
    "know the basics of coding and want to learn more about incorporating "
    "the Clash of Clans API into a project, you've come to the right place."

    "\n\nPlease click the Introduce button below to tell us a little "
    "bit about yourself and gain access to the rest of the server.")


class Welcome(commands.Cog):
    def __init__(self, bot: BotClient):
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.welcome")
        self.get_channel_cb = self.bot.settings.get_channel

    @commands.check(is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def recreate_welcome(self,
                               inter: ApplicationCommandInteraction):

        channel = self.bot.get_channel(self.get_channel_cb("welcome"))
        self.bot.log.debug(f"Purging {channel}")
        await channel.purge()

        self.bot.log.debug("Recreating welcome view")
        panel = await self.bot.inter_send(
            inter,
            title="Welcome to the Clash API Developers server!",
            panel=WELCOME_MESSAGE,
            return_embed=True,
            flatten_list=True)

        await channel.send(embed=panel[0], view=WelcomeView(self.bot))
        await self.bot.inter_send(inter,
                                  panel="Welcome recreated",)



def setup(bot):
    bot.add_cog(Welcome(bot))
