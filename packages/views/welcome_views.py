from logging import getLogger
from typing import TYPE_CHECKING

import disnake

from .base_views import BaseView
from .introduction_views import LanguageSelector
from ..config import BotMode

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
        temp_role = self.bot.settings.get_role("temp_guest")

        if inter.user.get_role(dev_role) is not None:
            await inter.send("You already have the developer role!",
                             ephemeral=True)
            return False

        if inter.user.get_role(temp_role) is not None:
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
        self.log.info(f"{inter.author} pressed the introduce button. "
                      f"Creating welcome thread.")

        thread: disnake.Thread = await inter.channel.create_thread(
            name=f"Welcome {inter.user.name}",
            type=disnake.ChannelType.private_thread,
            invitable=True,
            reason=f"User {inter.user.name} is introducing themselves"
        )

        self.log.debug(f"Created thread {thread.name} {thread.id}.")

        if self.bot.settings.mode == BotMode.DEV_MODE:
            me = self.bot.get_user(265368254761926667)
            await thread.send(me.mention, delete_after=5)
        else:
            await thread.send(f"<@&{self.bot.settings.get_role('admin')}>",
                              delete_after=5)

        await thread.add_user(inter.user)
        await thread.purge(limit=5)

        await inter.send("A private thread has been created for you. Please "
                         f"click on the thread and follow the prompts.\n{thread.jump_url}",
                         ephemeral=True,
                         delete_after=60 * 5)

        # Get the roles for the selector
        async with self.bot.pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT role_id, role_name, emoji_repr FROM bot_language_board;")

        await thread.send("Welcome. Please select the languages that you "
                          "are proficient in. You will be able to change "
                          f"this later.",
                          view=LanguageSelector(self.bot, records))

        self.log.info(f"User {inter.user} has been added to {thread.jump_url}")
