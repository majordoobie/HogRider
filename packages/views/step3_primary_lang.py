from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from packages.utils import models, utils
from packages.views.base_views import BaseView

if TYPE_CHECKING:
    from bot import BotClient

VIEW_TIMEOUT = 60 * 5


class PrimaryLanguageView(BaseView):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language],
                 member: disnake.Member) -> None:
        super().__init__(bot, timeout=VIEW_TIMEOUT)
        self.bot = bot
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.cls_name}")

        self.selection = PrimaryLanguageDropdown(self, bot, lang_records)
        self.member = member
        self.add_item(self.selection)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.log.warning(f"`{self.member}` timed out on `{self.cls_name}`")
        await utils.kick_user(self.bot, self.member)


class PrimaryLanguageDropdown(disnake.ui.StringSelect):
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
            placeholder="Choose your primary language",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        # Stops the views timeout
        self.view_instance.stop()
        langs = await self._get_langs()
