from typing import TYPE_CHECKING

import disnake

from asyncpg import Record

if TYPE_CHECKING:
    from bot import BotClient


class LanguageSelector(disnake.ui.View):
    def __init__(self, bot: "BotClient", lang_records: list[Record]) -> None:
        super().__init__(timeout=60 * 5)
        self.bot = bot
        self.selection = LanguageDropdown(bot, lang_records)
        self.add_item(self.selection)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.remove_item(self.selection)


class LanguageDropdown(disnake.ui.StringSelect):
    def __init__(self, bot: "BotClient", lang_records: list[Record]) -> None:
        self.bot = bot
        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.get("role_name"),
                emoji=lang.get("emoji_repr"),
                value=lang.get("role_id")))

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

        modal = IntroductionModal()
        await inter.response.send_modal(modal)

        print(modal.introduction)


class IntroductionModal(disnake.ui.Modal):
    def __init__(self):
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
        super().__init__(title="Introduction", components=components)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        await inter.response.send_message(
            "Thank you. An admin will be with you shortly.")

        self.introduction = inter.text_values.get("Introduction")
        self.languages = inter.text_values.get("Languages")
