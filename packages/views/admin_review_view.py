from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .base_views import BaseView
from ..config import BotMode
from ..utils import crud, models
from ..utils.utils import EmbedColor

if TYPE_CHECKING:
    from bot import BotClient


class AdminReviewView(BaseView):
    """
    Persistent view for admins to review the user application
    """

    def __init__(self, bot: "BotClient",
                 user: disnake.Member,
                 introduction: str,
                 languages: models.Language | None,
                 other_languages: str) -> None:
        super().__init__(bot, timeout=None)
        self.bot = bot
        self.user = user
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
        custom_id = f"{inter.user.id}_IM"

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            return modal_inter.custom_id == custom_id

        modal = DeclineModal(custom_id=custom_id)
        await inter.response.send_modal(modal)
        self.bot.log.debug(f"Sending admin {inter.user} the decline modal")
        await self.bot.wait_for("modal_submit", check=check)

        self.bot.log.info(f"{inter.user} has initiated a "
                          f"{'ban' if modal.ban else 'kick'} for applicant")

        if modal.ban:
            await self.user.ban(reason=modal.reason)
        else:
            await self.user.kick(reason=modal.reason)

        mod_log = self.bot.get_channel(
            self.bot.settings.get_channel("mod-log"))

        await self.bot.inter_send(
            mod_log,
            title=f"Member has been {'banned' if modal.ban else 'kick'} "
                  f"by {inter.user.name}",
            panel=f"**Reason:**\n{modal.reason}",
            author=self.user,
            color=EmbedColor.ERROR
        )

    @disnake.ui.button(label="More info",
                       style=disnake.ButtonStyle.blurple)
    async def more_info(self, button: disnake.ui.Button,
                        inter: disnake.MessageInteraction):
        await inter.response.defer()
        await inter.send(
            f"{self.user.mention} could you please provide "
            f"more information about how you plan on "
            f"using the API")


class DeclineModal(disnake.ui.Modal):
    def __init__(self, custom_id: str) -> None:
        self.reason: str = ("User took to long to reply or does not meet "
                            "the experience criteria.")
        self.ban: bool = False

        components = [
            disnake.ui.TextInput(
                label="Kick reason",
                placeholder=self.reason,
                custom_id="Reason",
                style=disnake.TextInputStyle.paragraph,
                min_length=0,
                max_length=1024,
                required=False
            ),
            disnake.ui.TextInput(
                label="[Y/N] Ban user? Ignore if just kick",
                placeholder="No",
                custom_id="Ban",
                style=disnake.TextInputStyle.short,
                min_length=0,
                max_length=5,
                required=False
            ),
        ]
        super().__init__(title="Reason for kicking user",
                         components=components,
                         custom_id=custom_id)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        reason = inter.text_values.get("Reason")
        if reason != "":
            self.reason = reason

        if inter.text_values.get("Ban").lower() in ["y", "yes", "yes"]:
            self.ban = True

        await inter.send("Please wait...")
