import logging
from typing import TYPE_CHECKING

import disnake
from disnake import Enum

from packages.views.base_views import BaseView

if TYPE_CHECKING:
    from bot import BotClient


class Confirmation(Enum):
    DECLINE = 0
    ACCEPT = 1


class Confirm(BaseView):
    def __init__(self, bot: "BotClient"):
        super().__init__(bot, timeout=None)
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")
        self.answer: Confirmation = Confirmation

    @disnake.ui.button(label="Accept", style=disnake.ButtonStyle.green)
    async def generic_accept(self, button: disnake.ui.Button,
                             inter: disnake.MessageInteraction):
        self.log.warning(f"`{inter.author}` clicked on `Accept`")
        self.answer = Confirmation.ACCEPT

    @disnake.ui.button(label="Decline", style=disnake.ButtonStyle.red)
    async def generic_decline(self, button: disnake.ui.Button,
                              inter: disnake.MessageInteraction):
        self.log.warning(f"`{inter.author}` clicked on `Decline`")
        self.answer = Confirmation.DECLINE
