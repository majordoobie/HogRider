import asyncio
from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from packages.config import BotMode
from packages.utils import crud, models, utils
from packages.views.base_views import BaseView
from packages.views.step3_admin_review import AdminReviewView
from packages.views.step3_primary_lang import PrimaryLanguageView

if TYPE_CHECKING:
    from bot import BotClient

VIEW_TIMEOUT = 60 * 15
MODAL_TIMEOUT = 60 * 10


class IntroductionModal(disnake.ui.Modal):
    def __init__(self, bot: "BotClient", custom_id: str) -> None:

        self.introduction: str = ""
        self.languages: str | None = None
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{bot.settings.log_name}.{self.cls_name}")

        components = [
            disnake.ui.TextInput(
                label="Intro",
                placeholder="Tell us what you plan to do with the CoC API",
                custom_id="Introduction",
                style=disnake.TextInputStyle.paragraph,
                min_length=32,
                max_length=1024,
                required=True
            ),
            disnake.ui.TextInput(
                label="[Optional] Other Languages",
                placeholder="Other languages we did not list",
                custom_id="Languages",
                style=disnake.TextInputStyle.short,
                min_length=0,
                max_length=128,
                required=False
            ),
        ]
        super().__init__(title="Introduction", components=components,
                         custom_id=custom_id)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        self.log.warning(f"`{inter.user}` submitted `{self.cls_name}`")

        self.introduction = inter.text_values.get("Introduction")
        self.languages = inter.text_values.get("Languages")

        await inter.response.edit_message(
            "Thank you. An admin will be with you shortly.")


class LanguageSelector(BaseView):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language],
                 member: disnake.Member,
                 custom_id: str) -> None:

        super().__init__(bot, timeout=VIEW_TIMEOUT, custom_id=custom_id)

        self.bot = bot
        self.langs: list[models.Language] | None = None
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")
        self.selection = LanguageDropdown(self, bot, lang_records)
        self.member = member
        self.add_item(self.selection)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.log.warning(f"`{self.member}` timed out on `{self.cls_name}`")
        await utils.kick_user(self.bot, self.member)


class LanguageDropdown(disnake.ui.StringSelect):
    def __init__(self,
                 view: disnake.ui.View,
                 bot: "BotClient",
                 lang_records: list[models.Language]) -> None:
        self.view_instance = view
        self.bot = bot
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")

        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.role_name,
                emoji=lang.emoji_repr,
                value=str(lang.role_id)
            ))

        comp_emoji = '🖥️'
        options.append(disnake.SelectOption(
            label="Other",
            value="Other",
            emoji=comp_emoji
        ))

        super().__init__(
            custom_id="Select Row",
            placeholder="Choose your languages",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        self.log.warning(f"`{inter.user}` has submitted `{self.cls_name}`")
        print("submitted")

        # Stops the views timeout
        self.view.langs = await self._get_langs()
        await inter.response.send_message("Tanks")
        self.view.stop()
        return

        primary_language = PrimaryLanguageView(self.bot, langs, inter.user)
        await inter.message.edit("Select", view=primary_language)
        print(primary_language)

        custom_id = f"{inter.user.id}_IM"
        modal = IntroductionModal(bot=self.bot,  custom_id=custom_id)

        self.log.warning(f"Sending `{inter.user}` the `{modal.cls_name}`")
        await inter.response.send_modal(modal)

        if await self._wait_for_modal(modal, custom_id, inter) is False:
            return

        msg = self._get_msg_payload(modal, langs)

        admin_panel = AdminReviewView(self.bot,
                                      inter.user,
                                      modal.introduction,
                                      langs,
                                      modal.languages)

        panel = await self.bot.inter_send(inter.channel,
                                          panel=msg,
                                          author=inter.author,
                                          flatten_list=True,
                                          return_embed=True)

        self.log.info(f"Adding admins to {inter.channel.jump_url}")
        if self.bot.settings.mode == BotMode.DEV_MODE:
            me = self.bot.get_user(265368254761926667)
            await inter.channel.send(me.mention, delete_after=5)
        else:
            await inter.channel.send(
                f"<@&{self.bot.settings.get_role('admin')}>",
                delete_after=5)

        await inter.channel.send(embed=panel[0], view=admin_panel)
        self.log.warning(f"Sending `{admin_panel.cls_name}` "
                         f"to {inter.channel.jump_url}")

    async def _get_langs(self) -> list[models.Language] | None:
        roles = []
        languages = await crud.get_languages(self.bot.pool)
        for lang in languages:
            if str(lang.role_id) in self.values:
                roles.append(lang)
        return roles

    async def _wait_for_modal(self,
                              modal: IntroductionModal,
                              custom_id: str,
                              inter: disnake.MessageInteraction) -> bool:

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

    @staticmethod
    def _get_msg_payload(modal: IntroductionModal,
                         langs: list[models.Language]) -> str:
        lang_repr = ""
        for lang in langs:
            lang_repr += f"{lang.emoji_repr}  "

        other_langs: str | None = None
        if modal.languages != "":
            other_langs = f"\n\n**Other Languages:**\n```{modal.languages}```"

        return (
            "**Introduction:**\n"
            f"{modal.introduction}\n\n"
            f"**Languages:**\n"
            f"{lang_repr}"
            f"{other_langs if other_langs else ''}"
        )
