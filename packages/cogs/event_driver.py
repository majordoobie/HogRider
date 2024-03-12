import logging
from datetime import datetime, timezone

import disnake
from disnake import RawMessageDeleteEvent
from disnake.ext import commands

from packages.utils import crud
from packages.utils.utils import EmbedColor
from bot import BotClient


class EventDriver(commands.Cog):
    def __init__(self, bot: BotClient):
        self.bot = bot
        self.log = logging.getLogger(
            f"{self.bot.settings.log_name}.EventDriver")
        self.guild_id = self.bot.settings.guild
        self.get_channel_cb = self.bot.settings.get_channel
        self.get_role_cb = self.bot.settings.get_role

    def _is_valid(self,
                  guild_id: int | None = None,
                  channel_id: int | None = None,
                  bot_user: disnake.Member | None = None) -> bool:
        """Small checker to ensure that the command is valid for an event"""

        if guild_id:
            if guild_id != self.guild_id:
                return False

        if channel_id:
            if channel_id == self.get_channel_cb("mod-log"):
                return False

        if bot_user:
            if bot_user.bot:
                return False

        return True

    @commands.Cog.listener()
    async def on_raw_thread_member_remove(
            self,
            payload: disnake.RawThreadMemberRemoveEvent) -> None:
        """Handle deleting the threads created when a user joins the channel,
        starts an introduction and they are either removed or they leave"""

        # Ignore if the thread is not from welcome
        if payload.thread.parent.id != self.bot.settings.get_channel(
                "welcome"):
            return

        if payload.cached_member:
            user = self.bot.get_user(payload.member_id).name
        else:
            user = payload.member_id

        self.bot.log.debug(
            f"User `{user}` has left the "
            f"welcome thread `{payload.thread}`")

        thread = await crud.get_thread_mgr(self.bot.pool, payload.thread.id)
        if thread is None:
            # TODO Handle this situation
            self.log.error("User left the thread but did not have a db "
                           "record for it. This should not happen to see "
                           f"what happen \n\n ```\n{payload}\n```")
            return

        if thread.user_id == payload.member_id:
            await payload.thread.delete(
                reason="Welcome thread deleted because applicant user left")
            self.bot.log.info(f"Thread `{payload.thread}` has been deleted")
            await crud.delete_thread_mgr(self.bot.pool, thread.thread_id)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member) -> None:
        """
        Notify of 3 things:
            - If  user is a bot, instruct the admins what to do next in
              regard to adding the bot to the server

            - If normal user and user is less than a month old, ping the
              admins that the account is new

            - Otherwise, just log that a user has joined the server
        """
        self.log.debug(f"User {member} has joined")

        timelapse = datetime.now(timezone.utc) - member.created_at
        years = timelapse.days // 365
        days = timelapse.days % 365

        mod_log = self.bot.get_channel(self.get_channel_cb("mod-log"))

        await self.bot.inter_send(
            mod_log,
            title="New member has joined",
            panel=(f"`{'User:':<10}` {member.name}\n"
                   f"`{'Acc Date:':<10}` {member.created_at.strftime('%Y%m%d %H:%M')}\n"
                   f"`{'Acc Age:':<10}` {years if years > 0 else 0} years {days} days\n"
                   f"`{'Is Bot:':<10}` {member.bot}"),
            author=member,
            color=EmbedColor.SUCCESS
        )

        channel = self.bot.get_channel(self.get_channel_cb("admin"))

        # Brand-new account, flag it
        if years == 0 and days < 30 and not member.bot:
            await self.bot.inter_send(
                channel,
                panel=f"New member, {member.name}, is less than one month old.",
                author=member,
                color=EmbedColor.ERROR
            )

        if member.bot:
            await self.bot.inter_send(
                channel,
                panel=f"{member.mention} has just been invited to the "
                      f"server. \nPerhaps it is time to set up a demo "
                      f"channel? (Ignore for now until the feature is ready)",
                author=member,
                color=EmbedColor.ERROR
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member) -> None:
        """
        Listener to indicate if a user has left the server
        """
        if not self._is_valid(guild_id=member.guild.id):
            return

        self.log.debug(f"Member `{member}` has left")

        timelapse = datetime.now(timezone.utc) - member.joined_at
        years = timelapse.days // 365
        days = timelapse.days % 365

        mod_log = self.bot.get_channel(self.get_channel_cb("mod-log"))

        await self.bot.inter_send(
            mod_log,
            title="Member left",
            panel=f"`{'User:':<12}` {member.name}\n"
                  f"`{'Member for':<12}` {years if years > 0 else 0} years {days} days",
            color=EmbedColor.ERROR,
            author=member
        )

        # Check for welcome thread and delete
        for thread in member.guild.threads:
            if thread.name == f"Welcome {member.name}":
                self.log.info(f"Removing thread \"Welcome {member.name}\"")
                try:
                    await thread.delete()
                except:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        """
        Log all messages into the database. This is required because the
        bot will only cache the most recent 1000 messages. If a user were
        to delete a message in discord, then the bot will not be able to
        log what message was deleted. To ensure that everyone is following the
        rules, the bot will log all messages and display them when a user
        deletes their message
        """
        if not self._is_valid(bot_user=message.author):
            return

        await crud.set_message(self.bot.pool, message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message,
                              after: disnake.Message):
        """
        Show a diff of the message that was edited.
        """
        if not before.content:
            return

        if before.content == after.content:
            return

        if not self._is_valid(guild_id=before.guild.id,
                              channel_id=before.channel.id,
                              bot_user=before.author
                              ):
            return

        self.log.debug(f"**Message Edit Event:**\n\n"
                       f"```\n{before.content}\n```\n\n"
                       f"```\n{after.content}\n```")

        mod_log = self.bot.get_channel(self.get_channel_cb("mod-log"))
        await self.bot.inter_send(
            mod_log,
            panel=(f"Message Link: {after.jump_url}\n\n"
                   f"**Before:**\n{before.content}\n\n"
                   f"**After:**\n{after.content}"),
            title=f"Message edited in #{before.channel.name}",
            footer=f"ID: {after.id} | {after.edited_at.strftime('%Y%d%m %H:%M:%S') if after.edited_at else None}",
            author=before.author
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        """
        Display in the logs what message was deleted and by who.
        """
        if not self._is_valid(guild_id=payload.guild_id,
                              channel_id=payload.channel_id,
                              bot_user=payload.cached_message.author if payload.cached_message else None):
            return

        msg = payload.cached_message.content if payload.cached_message else "No content"
        self.log.debug(f"**Message Delete Event:**\n\n"
                       f"```\n{msg}\n```")

        # Populate with the data that is going to be sent
        send_payload = {}

        if payload.cached_message:
            # Bet case scenario the message is cached in
            # the bot (only latest 1000 messages)
            message = payload.cached_message

            if message.author.bot:
                return

            send_payload["author"] = message.author
            send_payload["title"] = (f"Message deleted in "
                                     f"<#{message.channel.id}>")
            send_payload["panel"] = f"{message.content}\n\n{message.jump_url}"
            send_payload["footer"] = (f"ID: {message.id} | "
                                      f"{message.created_at.strftime('%Y%d%m %H:%M:%S')}")

        else:
            # if not cached, see if the message is in the db
            message = await crud.get_message(self.bot.pool, payload.message_id)

            user = self.bot.get_user(message.user_id)
            if user.bot:
                return

            if message:
                send_payload["author"] = self.bot.get_user(message.user_id)
                send_payload["title"] = (
                    f"Message deleted in <#{message.channel_id}>")
                send_payload["panel"] = message.content
                send_payload["footer"] = (f"ID: {message.message_id} | "
                                          f"{message.created_at}")

            else:
                # otherwise we are shit out of luck
                send_payload["title"] = (f"Message deleted in "
                                         f"<#{payload.channel_id}>")
                send_payload["panel"] = ("Message content was not "
                                         "saved into db or cached")
                send_payload["footer"] = f"ID: {payload.message_id}"

        mod_log = self.bot.get_channel(self.get_channel_cb("mod-log"))
        await self.bot.inter_send(
            mod_log,
            panel=send_payload.get("panel"),
            title=send_payload.get("title"),
            footer=send_payload.get("footer"),
            author=send_payload.get("author"),
            color=EmbedColor.ERROR
        )


def setup(bot):
    bot.add_cog(EventDriver(bot))
