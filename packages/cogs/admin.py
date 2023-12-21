import logging
import string
from random import choice, randint

from disnake.ext import commands

from packages.utils import utils
from config import GUILD_IDS


# TODO: Enable this feature once discord migration is up and running
# from cogs.utils import chat_exporter


class Admin(commands.Cog):
    GUILD_ID = 0
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.admin")
        Admin.GUILD_ID = bot.settings.guild

    @commands.command(name="lg", hidden=True)
    async def links_get(self, ctx, tag):
        """Get info from links api"""
        if tag.startswith("#"):
            payload = await self.bot.links.get_link(tag)
        else:
            payload = await self.bot.links.get_linked_players(tag)
        return await ctx.send(payload)

    # @commands.command(name="archive")
    # @commands.has_role("Admin")
    # async def archive_channel(self, ctx, limit: int = None):
    #     """Create html file with a transcript of the channel (Admin only)"""
    #     transcript = await chat_exporter.export(ctx.channel, limit=limit,
    #                                             bot=self.bot)
    #     if transcript is None:
    #         return await ctx.send("Nothing to export")
    #     transcript_file = discord.File(io.BytesIO(transcript.encode()),
    #                                    filename=f"transcript-{ctx.channel.name}.html"
    #                                    )
    #     await ctx.send(file=transcript_file)

    @commands.command(name="add_user", hidden=True)
    @commands.is_owner()
    async def add_user(self, ctx, usr):
        """Add user for coc discord links api (owner only)"""
        PUNCTUATION = "!@#$%^&*"
        pwd = choice(string.ascii_letters) + choice(PUNCTUATION) + choice(
            string.digits)
        characters = string.ascii_letters + PUNCTUATION + string.digits
        pwd += "".join(choice(characters) for x in range(randint(8, 12)))
        sql = "INSERT INTO coc_discord_users (username, passwd) VALUES ($1, $2)"
        await self.bot.pool.execute(sql, usr, pwd)
        await ctx.send(
            f"User: {usr} has been created with the following password:")
        await ctx.send(pwd)

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=GUILD_IDS)
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
    @commands.slash_command(guild_ids=GUILD_IDS)
    async def load_module(self, ctx, module: str):
        """
        Load a module into the running bot

        Parameters
        ----------
        module
            The module to load.
        """
        print(module)
        cog = f"{self.bot.settings.cog_path}.{module}"
        print(cog)
        try:
            self.bot.load_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module load error", exc_info=True)
            return
        await ctx.send(f"Loaded {cog} successfully")
        self.log.debug(f"Loaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=GUILD_IDS)
    async def unload_cog(self, ctx, module: str):
        """
        Unload a module from the running bot.

        Parameters
        ----------
        module
            The module to unload
        """
        cog = f"{self.bot.settings.cog_path}.{module}"
        try:
            self.bot.unload_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module unload error", exc_info=True)
            return
        await ctx.send(f"Unloaded {cog} successfully")
        self.log.debug(f"Unloaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=GUILD_IDS)
    async def re_load(self, ctx, module: str):
        """
        Reload a module from the running bot

        Parameters
        ----------
        module
            The module to reload
        """
        cog = f"{self.bot.settings.cog_path}.{module}"

        try:
            self.bot.reload_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module reload error", exc_info=True)
            return
        await ctx.send(f"Reloaded {cog} successfully")
        self.log.debug(f"Reloaded {cog} successfully")

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=GUILD_IDS)
    async def list_cogs(self, ctx):
        """
        List the loaded modules
        """
        output = ''
        for i in self.bot.settings.cogs_list:
            output += f"+ {i.split('.')[-1]}\n"
        await self.bot.send(ctx, output)


def setup(bot):
    bot.add_cog(Admin(bot))
