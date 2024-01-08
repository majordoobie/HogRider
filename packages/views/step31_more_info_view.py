from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .base_views import BaseView

if TYPE_CHECKING:
    from bot import BotClient


class ApplicantMoreInfo(BaseView):
    """
    Persistent view for admins to review the user application
    """

    def __init__(self,
                 bot: "BotClient",
                 user: disnake.User,
                 introduction: str
                 ) -> None:
        super().__init__(bot, timeout=None)
        self.bot = bot
        self.user = user
        self.introduction = introduction

        self.log = getLogger(f"{self.bot.settings.log_name}.ApplicantMoreInfo")

    async def interaction_check(self, inter: disnake.Interaction):
        admin_role = self.bot.settings.get_role("admin")

        if inter.user.get_role(admin_role) is None:
            await inter.send("We will be with you shortly. Please wait.",
                             ephemeral=True)
            return False

        return True

    @disnake.ui.button(label="Enter User Intro",
                       style=disnake.ButtonStyle.green)
    async def enter_info(self, button: disnake.ui.Button,
                         inter: disnake.MessageInteraction):
        custom_id = f"{self.user.id}_INTRO"

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            return modal_inter.custom_id == custom_id

        modal = ConsolidatedIntroModal(custom_id)
        await inter.response.send_modal(modal)

        self.bot.log.debug(f"Sending admin {inter.user} the "
                           f"consolidation intro modal")
        await self.bot.wait_for("modal_submit", check=check)
        self.introduction = modal.introduction

        self.stop()

    @disnake.ui.button(label="Use Original Intro",
                       style=disnake.ButtonStyle.green)
    async def original(self, button: disnake.ui.Button,
                       inter: disnake.MessageInteraction):
        await inter.response.send_message("Processing...", ephemeral=True)
        self.stop()

    @disnake.ui.button(label="Leave Intro Empty",
                       style=disnake.ButtonStyle.green)
    async def empty(self, button: disnake.ui.Button,
                    inter: disnake.MessageInteraction):
        await inter.response.send_message("Processing...", ephemeral=True)
        self.introduction = ""
        self.stop()


class ConsolidatedIntroModal(disnake.ui.Modal):
    def __init__(self, custom_id: str) -> None:
        self.introduction: str = ""

        components = [
            disnake.ui.TextInput(
                label="Introduction",
                placeholder="Paste the users introduction here...",
                custom_id="intro",
                style=disnake.TextInputStyle.paragraph,
                min_length=0,
                max_length=1024,
                required=False
            ),
        ]
        super().__init__(title="Consolidate User Introduction",
                         components=components,
                         custom_id=custom_id)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        self.introduction = inter.text_values.get("intro")
        await inter.send("Please wait...")
