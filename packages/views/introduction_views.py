from typing import TYPE_CHECKING

import disnake

from packages.utils import models

if TYPE_CHECKING:
    from bot import BotClient


class LanguageSelector(disnake.ui.View):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language]) -> None:
        super().__init__(timeout=60 * 5)
        self.bot = bot
        self.selection = LanguageDropdown(bot, lang_records)
        self.add_item(self.selection)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.remove_item(self.selection)


class LanguageDropdown(disnake.ui.StringSelect):
    def __init__(self, bot: "BotClient",
                 lang_records: list[models.Language]) -> None:
        self.bot = bot
        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.role_name,
                emoji=lang.emoji_repr,
                value=str(lang.role_id)
            ))

        options.append(disnake.SelectOption(
            label="Other",
            value="Other",
            emoji="💻"
        ))

        super().__init__(
            custom_id="Select Row",
            placeholder="Choose your languages",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        roles = []
        guild = self.bot.get_guild(self.bot.settings.guild)
        for role_id in self.values:
            roles.append(guild.get_role(role_id))

        await inter.message.edit("Thank you!", view=None)
        custom_id = f"{inter.user.id}_IM"

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            if modal_inter.custom_id == custom_id:
                return True
            return False

        modal = IntroductionModal(custom_id=custom_id)
        await inter.response.send_modal(modal)
        await self.bot.wait_for("modal_submit", check=check)

        print(modal.introduction)


class IntroductionModal(disnake.ui.Modal):
    def __init__(self, custom_id: str) -> None:
        self.introduction: str = ""
        self.languages: str | None = None

        components = [
            disnake.ui.TextInput(
                label="Intro",
                placeholder="Tell us what you plan to do with the CoC API",
                custom_id="Introduction",
                style=disnake.TextInputStyle.paragraph,
                min_length=15,
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
        self.introduction = inter.text_values.get("Introduction")
        self.languages = inter.text_values.get("Languages")
        await inter.response.edit_message(
            "Thank you. An admin will be with you shortly.")
