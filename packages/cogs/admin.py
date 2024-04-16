import logging
import re
from datetime import datetime, timezone

import disnake
from disnake.ext import commands, tasks

from packages.utils import utils
from packages.config import guild_ids, BotMode
from bot import BotClient
from packages.utils.utils import EmbedColor

SECTION_MATCH = re.compile(
    r'(?P<title>.+?)<a name="(?P<number>\d+|\d+.\d+)"></a>(?P<body>(.|\n)+?(?=(#{2,3}|\Z)))')
UNDERLINE_MATCH = re.compile(r"<ins>|</ins>")
URL_EXTRACTOR = re.compile(r"\[(?P<title>.*?)\]\((?P<url>[^)]+)\)")


# TODO: Enable this feature once discord migration is up and running
# from cogs.archive import chat_exporter


class Admin(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.admin")

        if self.bot.settings.mode == BotMode.LIVE_MODE:
            self.prune_users_task.start()

    @tasks.loop(hours=2)
    async def prune_users_task(self):
        count = await self._prune_users(guild=None)
        if count:
            self.log.error(f"Removed {count} inactive users from server")

    @prune_users_task.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.prune_users_task.cancel()

    @commands.command(name="lg", hidden=True)
    async def links_get(self, ctx, tag):
        """Get info from links api"""
        if tag.startswith("#"):
            payload = await self.bot.links.get_link(tag)
        else:
            payload = await self.bot.links.get_linked_players(tag)
        return await ctx.send(payload)

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def logout(self, ctx):
        """
        Kill the bot. Only use this if the bot is doing something insane.
        """
        self.log.error('Closing connections...')
        await self.bot.send(ctx, "Logging off")
        try:
            await self.bot.coc_client.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

        try:
            await self.bot.pool.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

        try:
            await self.bot.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def load_module(self, inter, module: str):
        """
        Load a module into the running bot

        Parameters
        ----------
        module
            The module to load.
        """
        await inter.response.defer()
        cog = f"{self.bot.settings.cog_path}.{module}"
        try:
            self.bot.load_extension(cog)
            self.bot.loaded_cogs.append(module)
        except Exception as error:
            await inter.send(error)
            self.log.error("Module load error", exc_info=True)
            return

        await self.bot.inter_send(inter,
                                  f"Loaded module {cog}",
                                  color=EmbedColor.SUCCESS)

        self.log.debug(f"Loaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def unload_cog(self, inter, module: str):
        """
        Unload a module from the running bot.

        Parameters
        ----------
        module
            The module to unload
        """
        await inter.response.defer()
        cog = f"{self.bot.settings.cog_path}.{module}"
        try:
            self.bot.unload_extension(cog)
            for index, cog in enumerate(self.bot.loaded_cogs):
                if cog == module:
                    self.bot.loaded_cogs.pop(index)

        except Exception as error:
            await inter.send(error)
            self.log.error("Module unload error", exc_info=True)
            return
        await self.bot.inter_send(inter,
                                  f"Unloaded module {cog}",
                                  color=EmbedColor.SUCCESS)
        self.log.debug(f"Unloaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def reload(self, inter, module: str):
        """
        Reload a module from the running bot

        Parameters
        ----------
        module
            The module to reload
        """
        await inter.response.defer()
        cog = f"{self.bot.settings.cog_path}.{module}"

        try:
            self.bot.reload_extension(cog)
        except Exception as error:
            await inter.send(error)
            self.log.error("Module reload error", exc_info=True)
            return
        await self.bot.inter_send(inter,
                                  f"Reloaded module {cog}",
                                  color=EmbedColor.SUCCESS)
        self.log.debug(f"Reloaded {cog} successfully")

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def list_cogs(self, ctx):
        """
        List the loaded modules
        """
        output = ''
        for i in self.bot.loaded_cogs:
            output += f"+ {i.split('.')[-1]}\n"

        await self.bot.send(ctx, output)

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def prune_users(self, inter: disnake.ApplicationCommandInteraction):
        """
        Remove users who have been in server for 14 days without a role
        """
        await inter.response.defer()
        count = await self._prune_users(inter.guild)
        await self.bot.inter_send(inter,
                                  f"Pruned {count} users",
                                  color=EmbedColor.SUCCESS)

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def recreate_rules(self,
                             inter: disnake.ApplicationCommandInteraction):
        """Recreate the #rules channel. (Admin only)


        Note
        -----
        This parses the Rules/code_of_conduct.md markdown file, and sends it
        as a series of embeds. Assumptions are made that each section is separated
        by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various
        messages.
        """
        await inter.response.defer()

        channel = self.bot.get_channel(
            self.bot.settings.get_channel("rules"))
        await channel.purge()

        with open("Rules/code_of_conduct.md", encoding="utf-8") as fp:
            text = fp.read()

        sections = SECTION_MATCH.finditer(text)

        embeds = []
        titles = []
        for match in sections:
            description = match.group("body")
            # underlines, dividers, bullet points
            description = UNDERLINE_MATCH.sub("__", description).replace("---",
                                                                         "").replace(
                "-", "\u2022")
            title = match.group("title").replace("#", "").strip()

            if "." in match.group("number"):
                colour = 0xBDDDF4  # lighter blue for sub-headings/groups
            else:
                colour = disnake.Colour.blue()

            embeds.append(
                disnake.Embed(title=title, description=description.strip(),
                              colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = disnake.ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(
                disnake.ui.Button(label=title.replace("#", "").strip(),
                                  url=message.jump_url))

        await channel.send(view=view)

        await self.bot.inter_send(
            inter,
            f"Rules have been recreated. View here <#{channel.id}>"
        )

    async def _prune_users(self, guild: disnake.Guild | None) -> int:
        """Remove all users that have been in the server for 14 days without a role"""
        if guild is None:
            guild = self.bot.get_guild(guild_ids()[0])

        count = 0
        for member in guild.members:
            if len(member.roles) == 1:
                timelapse = datetime.now(timezone.utc) - member.joined_at
                days = timelapse.days % 365
                if days > 14:
                    count += 1
                    await member.kick(reason=f"User has been in server for {days} without on-boarding")
        return count


def setup(bot):
    bot.add_cog(Admin(bot))
