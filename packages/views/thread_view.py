from typing import TYPE_CHECKING

import disnake

from packages.utils import crud, models
from packages.views.admin_review_view import AdminReviewView

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

    async def _get_langs(self) -> list[models.Language] | None:
        roles = []
        languages = await crud.get_languages(self.bot.pool)
        for lang in languages:
            if str(lang.role_id) in self.values:
                roles.append(lang)
        return roles

    async def callback(self, inter: disnake.MessageInteraction):

        await inter.message.edit("Thank you!", view=None)
        custom_id = f"{inter.user.id}_IM"

        def check(modal_inter: disnake.ModalInteraction) -> bool:
            if modal_inter.custom_id == custom_id:
                return True
            return False

        modal = IntroductionModal(custom_id=custom_id)
        await inter.response.send_modal(modal)
        self.bot.log.debug(f"Sending user {inter.user} the introduction modal")
        await self.bot.wait_for("modal_submit", check=check)

        langs = await self._get_langs()

        lang_repr = ""
        for lang in langs:
            lang_repr += f"{lang.emoji_repr}\n"

        other_langs: str | None = None
        if modal.languages != "":
            other_langs = f"\n\n**Other Languages:**\n```{modal.languages}```"

        msg = (
            "**Introduction:**\n"
            f"{modal.introduction}\n\n"
            f"**Languages:**\n"
            f"{lang_repr}"
            f"{other_langs if other_langs else ''}"
        )

        admin_panel = AdminReviewView(self.bot,
                                      modal.introduction,
                                      langs,
                                      modal.languages)

        panel = await self.bot.inter_send(inter.channel,
                                          panel=msg,
                                          author=inter.author,
                                          flatten_list=True,
                                          return_embed=True)

        await inter.channel.send(embed=panel[0], view=admin_panel)


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
