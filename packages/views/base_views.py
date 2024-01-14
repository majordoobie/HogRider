from logging import getLogger
import traceback
from typing import TYPE_CHECKING

import disnake

if TYPE_CHECKING:
    from bot import BotClient


class BaseView(disnake.ui.View):
    """
    Subclassed ui.View to add on_error logging
    """

    def __init__(self, bot: "BotClient", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")

    async def on_timeout(self) -> None:
        self.log.warning("View has timed out")

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
