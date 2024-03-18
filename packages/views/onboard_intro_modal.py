from logging import getLogger
from typing import TYPE_CHECKING

import disnake

if TYPE_CHECKING:
    from bot import BotClient

VIEW_TIMEOUT = 60 * 15
MODAL_TIMEOUT = 60 * 10


class IntroductionModal(disnake.ui.Modal):
    def __init__(self, bot: "BotClient", custom_id: str, modal_msg: str) -> None:
        self.introduction: str = ""
        self.custom_id = custom_id
        self.modal_msg = modal_msg
        self.languages: str | None = None
        self.cls_name = self.__class__.__name__
        self.log = getLogger(f"{bot.settings.log_name}.{self.cls_name}")

        components = [
            disnake.ui.TextInput(
                label="Intro",
                placeholder="What you plan to do with the CoC API? Provide brief examples "
                            "of the features your tool will have.",
                custom_id="Introduction",
                style=disnake.TextInputStyle.paragraph,
                min_length=80,
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

        await inter.response.send_message("Thank you! Standby please...")
