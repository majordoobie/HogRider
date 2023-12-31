from logging import getLogger
import traceback
from typing import TYPE_CHECKING

import disnake

if TYPE_CHECKING:
    from bot import BotClient


class BaseView(disnake.ui.View):
    """
    Class is a persistent listener with the introduce button. Whenever
    a user clicks on the button it will trigger this view to introduce
    the user with the moda.
    """

    def __init__(self, bot: "BotClient", *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(kwargs)
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.base_view")

    async def on_error(self,
                       error: Exception,
                       item: disnake.ui.Item,
                       inter: disnake.MessageInteraction) -> None:
        err_msg = "".join(
            traceback.format_exception(type(error),
                                       error,
                                       error.__traceback__,
                                       chain=True))

        self.log.error(
            f"**ui.View Error**\n\nItem: {item}\n\n```\n{err_msg}\n```")

