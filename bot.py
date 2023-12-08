import asyncio
import coc
import nextcord
import io
import sys
import traceback

import asyncpg
import nextcord

from config import Settings, BotMode

from cogs.utils import context
from cogs.utils import embedded_help
from coc.ext import discordlinks
from datetime import datetime
from nextcord.ext import commands
from loguru import logger

from fancy_logging import setup_logging

setup_logging("discord.application_command")

DESCRIPTION = (
    "Welcome to the Clash API Developers bot. This is a custom bot created by and for the users of the "
    "Clash API Developers Discord server. If you have questions, please reach out to "
    "@Admins on this server.")


# links_client = discordlinks.login(settings['links']['user'],
#                                   settings['links']['pass'])


class ApiBot(commands.Bot):
    def __init__(self, settings: Settings, coc_client: coc.Client,
                 pool: asyncpg.Pool, intents: nextcord.Intents):
        super().__init__(
            command_prefix=settings.bot_prefix,
            description=DESCRIPTION,
            case_insensitive=True,
            intents=intents,
            help_command=embedded_help.EmbeddedHelpCommand()
        )
        self.pool = pool
        self.settings = settings
        self.coc_client = coc_client
        self.color = nextcord.Color.greyple()
        self.logger = logger
        self.stats_board_id = None
        self.pending_members = {}
        self.loop.create_task(self.after_ready())

        for extension in self.settings.cogs_list:
            try:
                self.load_extension(extension)
                self.logger.debug(f"{extension} loaded successfully")
            except Exception as extension:
                self.logger.error(f"Failed to load extension {extension}.",
                                  file=sys.stderr)
                traceback.print_exc()

    @property
    def log_channel(self):
        return self.get_channel(self.settings.logs_channel)

    async def send_message(self, message):
        if len(message) > 2000:
            fp = io.BytesIO(message.encode())
            return await self.log_channel.send(
                file=nextcord.File(fp, filename='log_message.txt'))
        else:
            return await self.log_channel.send(message)

    def send_log(self, message):
        asyncio.ensure_future(self.send_message(message))

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)
        if ctx.command is None:
            return
        await self.invoke(ctx)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send(
                "This command cannot be used in private messages.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send(
                "Oops. This command is disabled and cannot be used.")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, nextcord.HTTPException):
                self.logger.error(f"In {ctx.command.qualified_name}:",
                                  file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                self.logger.error(f"{original.__class__.__name__}: {original}",
                                  file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)

    async def on_error(self, event_method, *args, **kwargs):
        e = nextcord.Embed(title="Discord Event Error", color=0xa32952)
        e.add_field(name="Event", value=event_method)
        e.description = f"```py\n{traceback.format_exc()}\n```"
        e.timestamp = datetime.utcnow()

        args_str = ["```py"]
        for index, arg in enumerate(args):
            args_str.append(f"[{index}]: {arg!r}")
        args_str.append("```")
        e.add_field(name="Args", value="\n".join(args_str), inline=False)
        try:
            await self.log_channel.send(embed=e)
        except:
            pass

    async def _initialize_db(self) -> None:
        """Could be done better. Placing this code here to not mess with the rest
        of the code base"""
        self.logger.debug("Initializing LanguageBoard table")
        language_table = """
            CREATE TABLE IF NOT EXISTS bot_language_board(
            role_id BIGINT PRIMARY KEY,
            role_name TEXT,
            emoji_id BIGINT,
            emoji_repr TEXT     -- Discord print format
        )"""

        mike_smells = """
            CREATE TABLE IF NOT EXISTS bot_smelly_mike (
            board_id BIGINT PRIMARY KEY DEFAULT 0
        )"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(language_table)
                await conn.execute(mike_smells)
                self.stats_board_id = await conn.fetchval(
                    "SELECT board_id FROM bot_smelly_mike")
                if not self.stats_board_id:
                    await conn.execute(
                        "INSERT INTO bot_smelly_mike (board_id) VALUES (0)")
        except Exception:
            self.logger.exception("Could not initialize LanguageBoard")

    async def on_ready(self):
        activity = nextcord.Activity(type=nextcord.ActivityType.watching,
                                     name="you write code")
        await self.change_presence(activity=activity)

    async def after_ready(self):
        await self.wait_until_ready()
        logger.add(self.send_log, level=self.settings.bot_log_level)
        if BotMode.LIVE_MODE == self.settings.mode:
            await self._initialize_db()
