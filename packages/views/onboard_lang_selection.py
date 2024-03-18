from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from packages.utils import crud, models, utils
from packages.views.base_views import BaseView

if TYPE_CHECKING:
    from bot import BotClient

VIEW_TIMEOUT = 60 * 15
MODAL_TIMEOUT = 60 * 10


class LanguageSelector(BaseView):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language],
                 member: disnake.Member,
                 modal: disnake.ui.Modal) -> None:
        super().__init__(bot, timeout=VIEW_TIMEOUT)

        self.bot = bot
        self.modal = modal
        self.langs: list[models.Language] | None = None
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")
        self.member = member

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

        self.lang_select_callback.options = options
        self.lang_select_callback.max_values = len(options)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.log.warning(f"`{self.member}` timed out on `{self.__class__.__name__}`")
        await utils.kick_user(self.bot, self.member)

    @disnake.ui.string_select(
        placeholder="Choose your language(s)",
        min_values=1,
    )
    async def lang_select_callback(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        self.log.warning(f"`{inter.user}` has submitted `{self.cls_name}`")

        # Stops the views timeout
        self.langs = await self._get_langs(select)

        if len(self.langs) > 1:
            await inter.response.defer()
        else:
            await inter.response.send_modal(modal=self.modal)
        self.stop()

    async def _get_langs(self, select: disnake.ui.StringSelect) -> list[models.Language] | None:
        roles = []
        languages = await crud.get_languages(self.bot.pool)
        for lang in languages:
            if str(lang.role_id) in select.values:
                roles.append(lang)
        return roles


class PrimaryLanguage(BaseView):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language],
                 member: disnake.Member,
                 modal: disnake.ui.Modal) -> None:
        super().__init__(bot, timeout=VIEW_TIMEOUT)

        self.bot = bot
        self.modal = modal
        self.lang_records = lang_records
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")
        self.member = member

        self.lang: models.Language | None = None

        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.role_name,
                emoji=lang.emoji_repr,
                value=str(lang.role_id)
            ))

        self.lang_select_callback.options = options

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.log.warning(f"`{self.member}` timed out on `{self.__class__.__name__}`")
        await utils.kick_user(self.bot, self.member)

    @disnake.ui.string_select(
        placeholder="Which of these is your primary language?",
        min_values=1,
        max_values=1
    )
    async def lang_select_callback(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        self.log.warning(f"`{inter.user}` has submitted `{self.cls_name}`")

        for lang in self.lang_records:
            if str(lang.role_id) in select.values:
                self.lang = lang
                break

        await inter.response.send_modal(modal=self.modal)
        self.stop()
