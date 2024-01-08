"""
Welcome view is the persistent window that all new users can see.
This file will handle the initial interaction with the introduction
button by creating a new thread for the user. Further interaction
inside the thread happens elsewhere.
"""
from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .base_views import BaseView
from .thread_view import LanguageSelector
from ..config import BotMode
from ..utils import crud, utils

if TYPE_CHECKING:
    from bot import BotClient


class WelcomeView(BaseView):
    """
    Class is a persistent listener with the introduce button. Whenever
    a user clicks on the button it will trigger this view to introduce
    the user with the moda.
    """

    def __init__(self, bot: "BotClient"):
        super().__init__(bot, timeout=None)
        self.bot = bot
        self.log = getLogger(f"{self.bot.settings.log_name}.WelcomeView")

    async def interaction_check(self, inter: disnake.Interaction):
        dev_role = self.bot.settings.get_role("developer")
        applicant_role = self.bot.settings.get_role("applicant")

        if inter.user.get_role(dev_role) is not None:
            await inter.send("You already have the developer role!",
                             ephemeral=True)
            return False

        if inter.user.get_role(applicant_role) is not None:
            await inter.send(
                "Your application is being processed, please be patient.",
                ephemeral=True)
            return False

        return True

    @disnake.ui.button(label="Introduce",
                       style=disnake.ButtonStyle.green,
                       custom_id="persistent_example:green")
    async def introduce(self, button: disnake.ui.Button,
                        inter: disnake.MessageInteraction):
        await inter.response.defer()

        # Give the user the applicant role
        applicant_role = utils.get_role(self.bot, "applicant")
        await inter.user.add_roles(applicant_role)

        self.log.info(f"{inter.author.name} pressed the introduce button. "
                      f"Creating welcome thread.")

        thread: disnake.Thread = await inter.channel.create_thread(
            name=f"Welcome {inter.user.name}",
            type=disnake.ChannelType.private_thread,
            invitable=True,
            reason=f"User {inter.user.name} is introducing themselves"
        )

        self.log.debug(f"Created thread {thread.name} {thread.jump_url}.")

        # Add the user then add them to the database so that we can clean up
        # the database after they are removed
        await thread.add_user(inter.user)
        await crud.set_thread_mgr(self.bot.pool, thread.id, inter.user.id,
                                  thread.created_at)

        await inter.send("A private thread has been created for you. Please "
                         f"click on the thread and follow the prompts.\n{thread.jump_url}",
                         ephemeral=True,
                         delete_after=60 * 5)

        records = await crud.get_languages(self.bot.pool)

        await thread.send("Welcome. Please select the languages that you "
                          "are proficient in. You will be able to change "
                          f"this later.",
                          view=LanguageSelector(self.bot, records))

        self.log.info(f"User {inter.user} has been added to {thread.jump_url}")
