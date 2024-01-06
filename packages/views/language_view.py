from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from packages.utils import crud, models, utils

if TYPE_CHECKING:
    from bot import BotClient


class LanguageView(disnake.ui.View):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language]) -> None:
        super().__init__(timeout=60 * 5)
        self.bot = bot
        self.selection = LanguageSelector(bot, lang_records)
        self.add_item(self.selection)
        self.log = getLogger(f"{self.bot.settings.log_name}.LanguageView")

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.remove_item(self.selection)


class LanguageSelector(disnake.ui.StringSelect):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language]) -> None:
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.LanguageView")
        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.role_name,
                emoji=lang.emoji_repr,
                value=str(lang.role_id)
            ))

        super().__init__(
            custom_id="Select Row",
            placeholder="Choose your languages",
            min_values=0,
            max_values=len(options),
            options=options,
        )

    async def _get_langs(self) -> list[disnake.Role] | None:
        roles = []
        for lang_id in self.values:
            roles.append(utils.get_role(self.bot, int(lang_id)))
        return roles

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.message.edit("Done.", view=None)
        roles = await self._get_langs()
        add_roles = []
        rm_roles = []

        for rm_role in inter.user.roles:
            if rm_role in roles:
                rm_roles.append(rm_role)
                await inter.user.remove_roles(rm_role)

        if rm_roles:
            role_names = "\n".join(i.name for i in rm_roles)
            self.log.info(f"Role Change: `{inter.user}`"
                          f"\nRemoved:\n```\n[{role_names}]\n```")

        for role in roles:
            if role not in rm_roles:
                add_roles.append(role)

        if add_roles:
            await inter.user.add_roles(*add_roles)
            role_names = "\n".join(i.name for i in add_roles)
            self.log.info(f"Role Change: `{inter.user}`"
                          f"\nAdded:\n```\n[{role_names}]\n```")

        # await inter.response.send_message("Done.", ephemeral=True)
