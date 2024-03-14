"""
This view is used for users that use the slash command to modify their languages
"""

from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from packages.utils import models, utils

if TYPE_CHECKING:
    from bot import BotClient


class LanguageView(disnake.ui.View):
    def __init__(self, bot: "BotClient",
                 lang_records: dict[int, models.MemberLanguage],
                 custom_id: str) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.selection = LanguageSelector(bot, lang_records, custom_id)
        self.add_item(self.selection)
        self.log = getLogger(f"{self.bot.settings.log_name}.LanguageView")

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.remove_item(self.selection)


class LanguageSelector(disnake.ui.StringSelect):
    def __init__(self, bot: "BotClient",
                 lang_records: dict[int, models.MemberLanguage],
                 custom_id: str) -> None:
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")
        self.langs = lang_records
        options = []

        self.log.debug("Logging example")

        for lang in lang_records.values():
            options.append(disnake.SelectOption(
                label=lang.role_name,
                emoji=lang.emoji_repr,
                value=str(lang.role_id),
                default=lang.present
            ))

        super().__init__(
            custom_id=custom_id,
            placeholder="Choose your languages",
            min_values=0,
            max_values=len(options),
            options=options,
        )

    async def _get_langs(self
                         ) -> tuple[
        list[models.MemberLanguage], list[models.MemberLanguage]]:
        """Return which roles will be modified"""
        previous_selected = [lang.role_id for lang in
                             self.langs.values() if lang.present]

        add_roles: list[models.MemberLanguage] = []
        rm_roles: list[models.MemberLanguage] = []

        sel_values = self.values if self.values else []

        # Populate roles to add
        for value in sel_values:
            lang = self.langs.get(int(value))
            lang.present = True
            add_roles.append(lang)

        # Populate roles to remove
        for value in previous_selected:
            if str(value) not in sel_values:
                lang = self.langs.get(value)
                lang.present = False
                rm_roles.append(lang)

        return add_roles, rm_roles

    async def callback(self, inter: disnake.MessageInteraction):
        add_roles, rm_roles = await self._get_langs()

        await inter.user.remove_roles(*[role.role for role in rm_roles])
        await inter.user.add_roles(*[role.role for role in add_roles])

        added = " ".join(role.emoji_repr for role in add_roles)
        added_msg = f"Added: {added}\n" if add_roles else ""

        removed = " ".join(role.emoji_repr for role in rm_roles)
        removed_msg = f"Removed: {removed}\n" if rm_roles else ""

        msg = f"Role Change: `{inter.user}`\n{added_msg}{removed_msg}"

        self.log.info(msg)
