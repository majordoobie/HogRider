import traceback
import logging

import coc
import asyncpg
import disnake
from disnake.ext import commands
from disnake import Forbidden, MessageInteraction
from disnake.ui import Item

from packages.config import Settings
from packages.utils.utils import EmbedColor
from packages.views.welcome_views import WelcomeView

DESCRIPTION = (
    "Welcome to the Clash API Developers bot. This is a custom bot created by and for the users of the "
    "Clash API Developers Discord server. If you have questions, please reach out to "
    "@Admins on this server.")


# links_client = discordlinks.login(settings['links']['user'],
#                                   settings['links']['pass'])

class ViewErr(disnake.ui.View):
    async def on_error(self, error: Exception, item: Item,
                       interaction: MessageInteraction) -> None:
        print("Yeah we got it")


class BotClient(commands.Bot):
    # limits
    EMBED_TITLE = 256
    EMBED_DESCRIPTION = 4096
    EMBED_FOOTER = 2048
    EMBED_AUTHOR = 256
    EMBED_TOTAL = 6000
    EMBED_SEND_TOTAL = 10

    def __init__(self, settings: Settings, coc_client: coc.Client,
                 pool: asyncpg.Pool, intents: disnake.Intents):
        super().__init__(
            command_prefix=settings.bot_prefix,
            description=DESCRIPTION,
            case_insensitive=True,
            intents=intents
        )
        self.pool = pool
        self.settings = settings
        self.coc_client = coc_client
        self.color = disnake.Color.greyple()
        self.stats_board_id = None
        self.log = logging.getLogger(f"{self.settings.log_name}.BotClient")

        # Persistent view
        self.welcome_view_init = False

        for extension in self.settings.cogs_list:
            try:
                self.load_extension(f"packages.cogs.{extension}")
                self.log.debug(f"{extension} loaded successfully...")
            except Exception as extension:
                self.log.error(f"Failed to load extension {extension}.",
                               exc_info=True)

        self.log.info("Bot is ready to go.")

    async def on_ready(self):
        activity = disnake.Activity(type=disnake.ActivityType.watching,
                                    name="you write code")
        await self.change_presence(activity=activity)

        # Init the welcome view to activate the listener
        if not self.welcome_view_init:
            self.welcome_view_init = True
            self.add_view(WelcomeView(self))

    async def on_resume(self):
        self.log.debug("Resuming connection...")

    async def on_slash_command(self,
                               inter: disnake.ApplicationCommandInteraction
                               ) -> None:
        """
        Function logs all the commands made by the users

        :param inter: disnake.ApplicationCommandInteraction
        :return:
        """

        space = 0
        if inter.options:
            space = max(len(option) + 1 for option in inter.options.keys())

        if space < 9:
            space = 9  # Length of the 'Command: ' key

        name = f"{inter.author.name}"
        msg = (
            f"**Command Log:**\n\n"
            f"`{'User:':<{space}}` {name}\n"
            f"`{'Command:':<{space}}` {inter.data.name}\n"
        )

        for option, data in inter.options.items():
            option = f"{option}:"

            if isinstance(data, disnake.Member):
                data: disnake.Member
                name = f"{data.name}"
                msg += f"`{option:<{space}}` {name}\n"
            else:
                msg += f"`{option:<{space}}` {data}\n"

        self.log.warning(f"{msg}")

    async def on_error(self, event, *args, **kwargs):
        self.log.error(traceback.format_exc())

    async def on_slash_command_error(
            self,
            inter: disnake.ApplicationCommandInteraction,
            error: commands.CommandError
    ) -> None:
        """
        Log all errors made by slash commands

        :param error:
        :param inter: disnake.ApplicationCommandInteraction
        :return:
        """
        # Catch all
        err_msg = "".join(
            traceback.format_exception(type(error),
                                       error,
                                       error.__traceback__,
                                       chain=True))

        # Catch all errors within command logic
        if isinstance(error, commands.CommandInvokeError):
            original = error.original
            # Catch errors such as roles not found
            if isinstance(original, disnake.InvalidData):
                await self.inter_send(inter, panel=original.args[0],
                                      title="INVALID OPERATION",
                                      color=EmbedColor.ERROR)
                self.log.error(f"{original.args[0]}\n\n```\n{err_msg}\n```")
                return

            # Catch permission issues
            elif isinstance(original, Forbidden):
                await self.inter_send(inter,
                                      panel="Even with proper permissions, the "
                                            "target user must be lower in the "
                                            "role hierarchy of this bot.",
                                      title="FORBIDDEN",
                                      color=EmbedColor.ERROR)
                self.log.error(f"{original.args[0]}\n\n```\n{err_msg}\n```")
                return

            else:
                await self.inter_send(inter,
                                      panel="Have an admin check the logs, please.",
                                      title="Sorry! I have an error.",
                                      color=EmbedColor.ERROR,
                                      return_embed=True
                                      )

                self.log.error("Error: The bot likely failed to reply to "
                               "the interaction", exc_info=True)
                return

        # Catch command.Check errors
        if isinstance(error, commands.CheckFailure):
            try:
                if error.args[0] == "Not owner":
                    await self.inter_send(inter, panel="Only doobie can run "
                                                       "this command",
                                          title="COMMAND FORBIDDEN",
                                          color=EmbedColor.ERROR)
                    return
            except:
                pass
            await self.inter_send(inter,
                                  panel="Only `Admin` are permitted "
                                        "to use this command",
                                  title="COMMAND FORBIDDEN",
                                  color=EmbedColor.ERROR)
            return

        # Catch all
        err = "".join(
            traceback.format_exception(type(error), error, error.__traceback__,
                                       chain=True))
        title = error.__class__.__name__
        if title is None:
            title = "Command Error"
        await self.inter_send(inter, panel=str(error), title=title,
                              color=EmbedColor.ERROR)

        self.log.error(err, exc_info=True)

    async def send(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            description,
            title='',
            color: EmbedColor = EmbedColor.INFO,
            code_block=False,
            _return=False,
            footnote=True,
            author: list | None = None) -> None | list:
        if not description:
            raise commands.BadArgument("No value to encapsulate in a embed")

        blocks = await self.text_splitter(description, code_block)
        embed_list = [disnake.Embed(
            title=f'{title}',
            description=blocks[0],
            color=color.value
        )]
        for i in blocks[1:]:
            embed_list.append(disnake.Embed(
                description=i,
                color=color.value
            ))
        if footnote:
            embed_list[-1].set_footer(text=self.settings.version)
        if author:
            embed_list[0].set_author(name=author[0], icon_url=author[1])

        if _return:
            return embed_list

        else:
            for i in embed_list:
                await ctx.send(embed=i)
        return

    async def inter_send(self,
                         inter: disnake.ApplicationCommandInteraction | disnake.MessageInteraction | None,
                         panel: str = "",
                         panels: list[str] | None = None,
                         title: str = "",
                         color: EmbedColor = EmbedColor.INFO,
                         code_block: bool = False,
                         footer: str = "",
                         author: disnake.Member = None,
                         view: disnake.ui.View = None,
                         return_embed: bool = False,
                         flatten_list: bool = False
                         ) -> list[disnake.Embed] | list[list[disnake.Embed]]:
        """
        Wrapper function to print embeds

        :param flatten_list: If a single list of embeds should be returned
        :param return_embed: If the embed should be returned instead of printing
        :param view: Optional view to submit
        :param panel: Text to send
        :param author: Optional author to send
        :param footer: Optional footer to use
        :param code_block: If the text should be in a code block
        :param color: Color to use for the embed
        :param title: The optional title of the embed
        :param inter: The Interaction object
        :param panels: Optional list of panels to send
        """
        total_panels = []
        input_panels = []

        if panels:
            for i in panels:
                input_panels.append(i)
        else:
            input_panels.append(panel)

        for panel in input_panels:
            for sub_panel in await self.text_splitter(panel, code_block):
                total_panels.append(sub_panel)

        last_index = len(total_panels) - 1
        total_embeds = []
        embeds = []
        author_set = False
        for index, panel in enumerate(total_panels):
            embed = disnake.Embed(
                description=panel,
                color=color.value,
                title=title if index == 0 else "",
            )

            if index == 0:
                if author and not author_set:
                    author_set = True
                    embed.set_author(
                        name=author.display_name,
                        icon_url=author.avatar.url if author.avatar else None
                    )

            if index == last_index:
                if footer != "":
                    embed.set_footer(text=footer)

            # If the current embed is going to make the embeds block exceed
            # to send size, then create a new embed block
            embeds_size = sum(len(embed) for embed in embeds)
            if len(embeds) == BotClient.EMBED_SEND_TOTAL:
                total_embeds.append(embeds.copy())
                embeds = []

            if embeds_size + len(embed) > BotClient.EMBED_TOTAL:
                total_embeds.append(embeds.copy())
                embeds = []

            embeds.append(embed)

        if embeds:
            total_embeds.append(embeds)

        if return_embed:
            if flatten_list:
                return [embed for embed_list in total_embeds for embed in
                        embed_list]
            return total_embeds

        if hasattr(inter, "response"):
            # send_func = inter.response.send_message
            send_func = inter.send
        else:
            send_func = inter.send

        last_embed = len(total_embeds) - 1
        for index, embeds in enumerate(total_embeds):
            if last_embed == index and view:
                await send_func(embeds=embeds, view=view)
            else:
                await send_func(embeds=embeds)

    @staticmethod
    async def text_splitter(text: str, code_block: bool = False) -> list[str]:
        """Split text into blocks and return a list of blocks"""
        blocks = []
        block = ''
        for i in text.split('\n'):
            if (len(i) + len(block)) > BotClient.EMBED_DESCRIPTION:
                block = block.rstrip('\n')
                if code_block:
                    blocks.append(f'```{block}```')
                else:
                    blocks.append(block)
                block = f'{i}\n'
            else:
                block += f'{i}\n'
        if block:
            if code_block:
                blocks.append(f'```{block}```')
            else:
                blocks.append(block)
        return blocks
