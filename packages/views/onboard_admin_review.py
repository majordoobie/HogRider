from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .step31_more_info_view import ApplicantMoreInfo
from .base_views import BaseView
from ..utils import models, utils

if TYPE_CHECKING:
    from bot import BotClient


class AdminReviewView(BaseView):
    """
    Persistent view for admins to review the user application
    """

    def __init__(self, bot: "BotClient",
                 member: disnake.Member,
                 introduction: str,
                 langs: list[models.Language] | None,
                 other_languages: str,
                 primary_lang: models.Language | None) -> None:
        super().__init__(bot, timeout=None)
        self.cls_name = self.__class__.__name__
        self.bot = bot
        self.member = member
        self.introduction = introduction
        self.langs = langs
        self.primary_lang = primary_lang
        self.other_languages = other_languages
        self.more_info = False

        # Result values
        self.accept_user: bool = False
        self.final_introduction: str
        self.approving_user: disnake.Member

        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")

    async def interaction_check(self, inter: disnake.Interaction):
        admin_role = self.bot.settings.get_role("admin")

        if inter.user.get_role(admin_role) is None:
            await inter.send("We will be with you shortly. Please wait.",
                             ephemeral=True)
            return False

        return True

    def log_press(self, inter: disnake.MessageInteraction, button: str) -> str:
        return f"`{inter.user}` clicked on `{button}` for `{self.member}`"

    @disnake.ui.button(label="Accept",
                       style=disnake.ButtonStyle.green)
    async def accept(self, button: disnake.ui.Button,
                     inter: disnake.MessageInteraction):

        self.log.warning(self.log_press(inter, "Accept"))
        self.accept_user = True

        await inter.response.defer()

        roles = [utils.get_role(self.bot, lang.role_id) for lang in
                 self.langs]

        roles.append(utils.get_role(self.bot, "developer"))
        applicant_role = utils.get_role(self.bot, "applicant")

        await self.member.remove_roles(applicant_role)
        await self.member.add_roles(*roles, atomic=True)

        old_name = self.member.nick if self.member.nick else self.member.name

        if self.primary_lang:
            try:
                await self.member.edit(nick=f"{old_name} | {self.primary_lang.role_name}")
            except disnake.HTTPException:
                self.log.critical(f"Could not edit `{self.member}` name due to length")

        self.log.error(f"Enrolling {self.member}\nNew Name: `{self.member.nick}`\n"
                       f"New Roles: `{', '.join(i.role_name for i in self.langs)}`")

        if self.more_info:
            self.final_introduction = await self._get_introduction(self.bot, inter,
                                                                   self.introduction)
        else:
            self.final_introduction = self.introduction

        self.approving_user = inter.user
        self.stop()

    @disnake.ui.button(label="Decline",
                       style=disnake.ButtonStyle.red)
    async def decline(self, button: disnake.ui.Button,
                      inter: disnake.MessageInteraction):
        self.log.warning(self.log_press(inter, "Decline"))

        custom_id = f"{inter.user.id}_IM"

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            return modal_inter.custom_id == custom_id

        modal = DeclineModal(custom_id=custom_id)
        await inter.response.send_modal(modal)

        await self.bot.wait_for("modal_submit", check=check)

        self.bot.log.warning(f"`{inter.user}` has initiated a "
                             f"{'ban' if modal.ban else 'kick'} for applicant")

        if modal.ban:
            await self.member.ban(reason=modal.reason)
        else:
            await self.member.kick(reason=modal.reason)

        mod_log = self.bot.get_channel(
            self.bot.settings.get_channel("mod-log"))

        await self.bot.inter_send(
            mod_log,
            title=f"Member has been {'banned' if modal.ban else 'kick'} "
                  f"by {inter.user.name}",
            panel=f"**Reason:**\n{modal.reason}",
            author=self.member,
            color=utils.EmbedColor.ERROR
        )

        self.stop()

    @disnake.ui.button(label="More info",
                       style=disnake.ButtonStyle.blurple)
    async def more_info(self, button: disnake.ui.Button,
                        inter: disnake.MessageInteraction):
        self.log.warning(self.log_press(inter, "More Info"))
        self.more_info = True
        await inter.response.defer()
        await inter.send(
            f"{self.member.mention} could you please provide "
            f"more information about how you plan on "
            f"using the API")

    @disnake.ui.button(label="Learning Server",
                       style=disnake.ButtonStyle.blurple)
    async def learning_server(self, button: disnake.ui.Button,
                              inter: disnake.MessageInteraction):

        self.log.warning(self.log_press(inter, "Learning Server"))
        self.more_info = True
        await inter.response.defer()
        await inter.send(
            f"Hi, {self.member.mention}! This server is mainly about the APIs Supercell provides "
            f"about their games. While requesting general coding help is allowed, "
            f"it's not the main purpose of the server. What experience do you have with coding?")

    async def _get_introduction(self, bot: "BotClient",
                                inter: disnake.MessageInteraction,
                                introduction: str) -> str:
        self.log.debug(f"Presenting `{inter.user}` with the "
                       f"ApplicationMoreInfo modal")

        view = ApplicantMoreInfo(self.bot, inter.user, introduction)

        panel = await self.bot.inter_send(
            inter.channel,
            panel="Please collect the users message that will be pasted in "
                  "the modal. When ready, click on the button.",
            flatten_list=True,
            return_embed=True)

        await inter.send(embed=panel[0], view=view, ephemeral=True)
        await view.wait()
        return view.introduction


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
