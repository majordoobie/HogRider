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
        super().__init__(timeout=kwargs.get("timeout"))
        self.bot = bot
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")
        self.custom_id = kwargs.get("custom_id")

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

    async def wait_for(self,
                       modal: disnake.ui,
                       custom_id: str,
                       inter: disnake.MessageInteraction,
                       timeout: int = 60) -> bool:

        success_submit = True

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            return modal_inter.custom_id == custom_id

        try:
            await self.bot.wait_for("modal_submit",
                                    check=check,
                                    timeout=MODAL_TIMEOUT)
            self.log.info(f"`{inter.user}` has submitted `{modal.cls_name}`")

        except asyncio.TimeoutError:
            self.log.warning(f"`{inter.user}` timed out on`{modal.cls_name}`")
            self.view_instance.stop()
            await utils.kick_user(self.bot, inter.user)
            success_submit = False

        return success_submit
