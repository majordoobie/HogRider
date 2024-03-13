"""
File will handle the on-boarding process of the person that clicked on "Introduce". This will call each of the
views that are needed to complete the on-boarding process.
"""
import asyncio
from typing import TYPE_CHECKING
from logging import getLogger

import disnake

from .step2_thread_view import LanguageSelector
from ..utils import crud, utils
from .base_views import BaseView

if TYPE_CHECKING:
    from bot import BotClient

class OnboardMgr:
    def __init__(self, bot: "BotClient", thread: disnake.Thread, user: disnake.Member) -> None:
        self.thread = thread
        self.user = user
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

    async def on_board(self) -> None:
        records = await crud.get_languages(self.bot.pool)

        self.log.info(f"User `{self.user}` has been added to "
                      f"{self.thread.jump_url} and the language "
                      f"select panel has been presented to them.")

        custom_id = f"{self.user.id}_lang_select"

        lang_selector_view = LanguageSelector(self.bot, records, self.user, custom_id)

        def check(modal_inter: disnake.MessageInteraction) -> bool:
            print("I am here")
            print(modal_inter.data)
            return f"{modal_inter.user.id}_lang_select" == custom_id


        await self.thread.send("Welcome. Please select the languages that you "
                          "are proficient in. You will be able to change "
                          f"this later.",
                          view=lang_selector_view)

        try:
            await self.bot.wait_for("dropdown", check=check)
            print("Drop down was clicked")

        except asyncio.TimeoutError:
            print("Errored out dude")


        print(lang_selector_view)
        print(dir(lang_selector_view))
        print(lang_selector_view.langs)
