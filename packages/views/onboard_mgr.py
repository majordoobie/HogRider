"""
File will handle the on-boarding process of the person that clicked on "Introduce". This will call each of the
views that are needed to complete the on-boarding process.
"""
import asyncio
from typing import TYPE_CHECKING
from logging import getLogger

import disnake

from .onboard_lang_selection import LanguageSelector, PrimaryLanguage
from .onboard_intro_modal import IntroductionModal
from .onboard_admin_review import AdminReviewView
from ..config import BotMode
from ..utils import crud, utils, models

if TYPE_CHECKING:
    from bot import BotClient

MODAL_TIMEOUT = 60 * 10


class OnboardMgr:
    def __init__(self, bot: "BotClient",
                 thread: disnake.Thread,
                 inter: disnake.MessageInteraction,
                 user: disnake.Member) -> None:
        self.thread = thread
        self.user = user
        self.bot = bot
        self.inter = inter
        self.log = getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

    async def on_board(self) -> None:
        self.log.debug(f"User `{self.user}` has been added to "
                       f"{self.thread.jump_url} and the language "
                       f"select panel has been presented to them.")

        # Modal object will be sent out to the lang functions since
        # we need to piggyback off the interaction response
        custom_id = f"MODAL_{self.user.id}"
        modal_msg = "Thank you! Now please use the modal to answer a few questions."
        modal = IntroductionModal(bot=self.bot, custom_id=custom_id, modal_msg=modal_msg)

        # Fetch the languages and primary langauge of the user
        # the primary language is used to determine their name change
        self.log.debug(f"Sending `{self.user}` `{LanguageSelector.__class__.__name__}`")
        msg, langs = await self._get_languages(modal)

        # Determine if we need to request their primary language for the name change
        if len(langs) > 1:
            self.log.debug(f"Sending `{self.user}` `{PrimaryLanguage.__class__.__name__}`")
            primary_lang = await self._get_primary_lang(msg, langs, modal)
            self.log.debug(f"User `{self.user} primary language set to `{primary_lang.role_name}`")

        else:
            if langs:
                primary_lang = langs[0]
            else:
                primary_lang = None
            self.log.debug(f"User `{self.user}` primary language set to `{primary_lang.role_name}`")
            await msg.edit(modal.modal_msg, embed=None, view=None)

        # The two language functions will handle sending the user the modal with their
        # callbacks. Here, we instruct the bot to wait for the modal to be submitted so
        # that we can act on it.
        modal_response = await self._get_introduction(modal=modal)
        if modal_response is None:
            return

        msg_payload = self._get_msg_payload(modal, langs)

        admin_view = AdminReviewView(self.bot,
                                     self.user,
                                     modal.introduction,
                                     langs,
                                     modal.languages)

        panel = await self.bot.inter_send(self.inter,
                                          panel=msg_payload,
                                          author=self.user,
                                          flatten_list=True,
                                          return_embed=True)

        self.log.warning(f"Adding admins to {self.thread.jump_url}")

        if self.bot.settings.mode == BotMode.DEV_MODE:
            me = self.bot.get_user(265368254761926667)
            await self.thread.send(me.mention, delete_after=5)
        else:
            await self.thread.send(
                f"<@&{self.bot.settings.get_role('admin')}>",
                delete_after=5)

        await self.thread.send(embed=panel[0], view=admin_view)
        await admin_view.wait()


        mod_log = self.bot.get_channel(
            self.bot.settings.get_channel("mod-log"))

        general_channel = self.bot.get_channel(
            self.bot.settings.get_channel("general")
        )

        lang_repr = ""
        for lang in langs:
            lang_repr += f"{lang.emoji_repr} "

        other_langs: str | None = None
        if admin_view.other_languages != "":
            other_langs = (f"\n\n**Other Languages:**\n```"
                           f"{admin_view.other_languages}```")

        msg = (
            "**Introduction:**\n"
            f"{admin_view.final_introduction}\n\n"
            f"**Languages:**\n"
            f"{lang_repr}"
            f"{other_langs if other_langs else ''}"
        )

        await self.bot.inter_send(
            mod_log,
            title=f"User {self.user} has been approved by {inter.user}",
            panel=msg,
            author=self.member,
            color=utils.EmbedColor.SUCCESS
        )

        await self.bot.inter_send(
            general_channel,
            title=f"Please welcome `{self.member}`!",
            panel=msg,
            author=self.member,
            color=utils.EmbedColor.SUCCESS
        )

        # This will trigger the delete event
        await inter.channel.remove_user(self.member)
        self.log.debug(f"Removed {self.member} from the thread")


        await msg.delete()
        print("other langs: ", modal.languages)
        print("intro: ", modal.introduction)
        print("primary: ", primary_lang)
        print("langs: ", langs)

    async def _get_introduction(self, modal: IntroductionModal) -> IntroductionModal | None:
        self.log.debug(f"Sending `{self.user}` `{modal.__class__.__name__}`")
        try:
            await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == modal.custom_id and i.author.id == self.user.id,
                timeout=MODAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.log.warning(f"`{self.user}` timed out on `{modal.__class__.__name__}`")
            await utils.kick_user(self.bot, self.user)
            return None

        return modal

    async def _get_languages(self,
                             modal: disnake.ui.Modal) -> tuple[disnake.Message, list[models.Language]]:
        """
        This handles the first interactive component with the user. It will ask the user what languges they
        know. This information will be used to assign new roles and new name
        """
        records = await crud.get_languages(self.bot.pool)

        lang_selector_view = LanguageSelector(self.bot, records, self.user, modal)

        msg_text = ("\n\nSelecting languages here will unlock the help channel for those languages. This can "
                    "always be changed later!"
                    )

        panel = await self.bot.inter_send(self.inter,
                                          title="What languages are you proficient in?",
                                          panel=msg_text,
                                          author=self.user,
                                          flatten_list=True,
                                          return_embed=True)
        msg = await self.thread.send(
            embed=panel[0],
            view=lang_selector_view)

        await lang_selector_view.wait()
        return msg, lang_selector_view.langs

    async def _get_primary_lang(self, msg: disnake.Message,
                                langs: list[models.Language],
                                modal: IntroductionModal) -> models.Language:

        primary_language_view = PrimaryLanguage(self.bot, langs, self.user, modal)

        msg_text = ("\n\nThank you for the selection!\n\nNow, out of the languages you selected, "
                    "which one would you say is your primary language?")

        panel = await self.bot.inter_send(self.inter,
                                          title="Which language is your primary?",
                                          panel=msg_text,
                                          author=self.user,
                                          flatten_list=True,
                                          return_embed=True)
        msg = await msg.edit(
            embed=panel[0],
            view=primary_language_view)

        await primary_language_view.wait()
        await msg.edit(modal.modal_msg, embed=None, view=None)

        return primary_language_view.lang

    async def on_timeout(self):
        print("Got the timeout")


    @staticmethod
    def _get_msg_payload(modal: IntroductionModal,
                         langs: list[models.Language]) -> str:
        lang_repr = ""
        for lang in langs:
            lang_repr += f"{lang.emoji_repr}  "

        other_langs: str | None = None
        if modal.languages != "":
            other_langs = f"\n\n**Other Languages:**\n```{modal.languages}```"

        return (
            "**Introduction:**\n"
            f"{modal.introduction}\n\n"
            f"**Languages:**\n"
            f"{lang_repr}"
            f"{other_langs if other_langs else ''}"
        )

"""

        admin_panel = AdminReviewView(self.bot,
                                      inter.user,
                                      modal.introduction,
                                      langs,
                                      modal.languages)

        panel = await self.bot.inter_send(inter.channel,
                                          panel=msg,
                                          author=inter.author,
                                          flatten_list=True,
                                          return_embed=True)

        self.log.info(f"Adding admins to {inter.channel.jump_url}")
        if self.bot.settings.mode == BotMode.DEV_MODE:
            me = self.bot.get_user(265368254761926667)
            await inter.channel.send(me.mention, delete_after=5)
        else:
            await inter.channel.send(
                f"<@&{self.bot.settings.get_role('admin')}>",
                delete_after=5)

        await inter.channel.send(embed=panel[0], view=admin_panel)
        self.log.warning(f"Sending `{admin_panel.cls_name}` "
                         f"to {inter.channel.jump_url}")
                         

"""
