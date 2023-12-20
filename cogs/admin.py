import logging
import string
import traceback
from random import choice, randint

from disnake.ext import commands


# TODO: Enable this feature once discord migration is up and running
# from cogs.utils import chat_exporter


class Admin(commands.Cog):
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.admin")

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    def get_syntax_error(self, e):
        if e.text is None:
            return f"```py\n{e.__class__.__name__}: {e}\n```"
        return f"```py\n{e.text}{'^':>{e.offset}}\n{e.__class__.__name__}: {e}```"

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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, module):
        """Loads a module. (owner only)"""
        try:
            await self.bot.load_extension(module)
            self.log.debug(f"{module} loaded successfully")
        except commands.ExtensionError as error:
            await ctx.send(error)
            self.log.error("Loading failure...", exc_info=True)
        else:
            await ctx.send("\N{OK HAND SIGN}")
            self.log.info(f"Reloaded module {module}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, module):
        """Unloads a module. (owner only)"""
        try:
            await self.bot.unload_extension(module)
            self.log.debug(f"{module} unloaded successfully")
        except commands.ExtensionError as error:
            await ctx.send(error)
            self.log.error("Unloading failure...", exc_info=True)
        else:
            await ctx.send("\N{OK HAND SIGN}")
            self.log.info(f"Unloaded module {module}")


def setup(bot):
    bot.add_cog(Admin(bot))
