from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .base_views import BaseView
from ..config import BotMode
from ..utils import crud, models

if TYPE_CHECKING:
    from bot import BotClient


class AdminReviewView(BaseView):
    """
    Class is a persistent listener with the introduce button. Whenever
    a user clicks on the button it will trigger this view to introduce
    the user with the moda.
    """

    def __init__(self, bot: "BotClient",
                 introduction: str,
                 languages: models.Language | None,
                 other_languages: str) -> None:
        super().__init__(bot, timeout=None)
        self.bot = bot
        self.introduction = introduction
        self.languages = languages
        self.other_languages = other_languages

        self.log = getLogger(f"{self.bot.settings.log_name}.AdminReview")

    async def interaction_check(self, inter: disnake.Interaction):
        admin_role = self.bot.settings.get_role("admin")

        if inter.user.get_role(admin_role) is None:
            await inter.send("We will be with you shortly. Please wait.",
                             ephemeral=True)
            return False

        return True

    @disnake.ui.button(label="Accept",
                       style=disnake.ButtonStyle.green)
    async def accept(self, button: disnake.ui.Button,
                     inter: disnake.MessageInteraction):
        await inter.response.defer()
        await inter.send("Accepting")

    @disnake.ui.button(label="Decline",
                       style=disnake.ButtonStyle.red)
    async def decline(self, button: disnake.ui.Button,
                      inter: disnake.MessageInteraction):
        await inter.response.defer()
        await inter.send("Declining")

    @disnake.ui.button(label="More info",
                       style=disnake.ButtonStyle.blurple)
    async def mode_info(self, button: disnake.ui.Button,
                     inter: disnake.MessageInteraction):
        await inter.response.defer()
        await inter.send("Need more info")
