import logging

import asyncpg
import disnake
from disnake import RawMessageDeleteEvent
from disnake.ext import commands

from packages.utils.utils import EmbedColor


class EventDriver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(
            f"{self.bot.settings.log_name}.EventDriver")
        self.guild_id = self.bot.settings.guild
        self.get_channel_cb = self.bot.settings.get_channel
        self.get_role_cb = self.bot.settings.get_role

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Log all messages to be able to query it on_delete"""
        if message.author.bot:
            return

        async with self.bot.pool.acquire() as conn:
            sql = ("INSERT INTO user_message "
                   "(message_id, user_id, channel_id, create_date, content) "
                   "VALUES ($1, $2, $3, $4, $5)")

            await conn.execute(sql,
                               message.id,
                               message.author.id,
                               message.channel.id,
                               message.created_at,
                               message.content)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message,
                              after: disnake.Message):
        if not before.content:
            return
        self.log.debug(f"Message Edit Event: {before.content} \n {before}")

        if before.guild.id != self.guild_id:
            return

        if before.channel.id == self.get_channel_cb("mod-log"):
            return

        if before.author.bot:
            return

        mod_channel = self.bot.get_channel(self.get_channel_cb("mod-log"))

        await self.bot.inter_send(
            mod_channel,
            panel=(f"Message Link: {after.jump_url}\n\n"
                   f"**Before:**\n{before.content}\n\n"
                   f"**After:**\n{after.content}"),
            title=f"Message edited in #{before.channel.name}",
            footer=f"ID: {after.id} | {after.edited_at.strftime('%Y%d%m %H:%M:%S')}",
            author=before.author
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        self.log.debug(f"Message Raw Event: {payload}")

        if payload.guild_id != self.guild_id:
            return

        if payload.channel_id == self.get_channel_cb("mod-log"):
            return

        mod_channel = self.bot.get_channel(self.get_channel_cb("mod-log"))

        # Populate with the data that is going to be sent
        send_payload = {}

        if payload.cached_message:
            # Bet case scenario the message is cached in
            # the bot (only latest 1000 messages)
            message = payload.cached_message
            self.log.debug(f"Debug content: {message.content}")

            send_payload["panel"] = f"{message.content}\n\n{message.jump_url}"
            send_payload["title"] = f"Message deleted in #{message.channel.name}"
            send_payload["footer"] = f"ID: {message.id} | {message.created_at.strftime('%Y%d%m %H:%M:%S')}"
            send_payload["author"] = message.author

        else:
            # if not cached, see if the message is in the db
            record: asyncpg.Record | None = None
            async with self.bot.pool.acquire() as conn:
                record = await conn.fetchrow(
                    "SELECT * FROM user_message WHERE message_id = $1",
                    payload.message_id)

            if record:
                send_payload["panel"] = record.get("content", "")
                send_payload["title"] = f"Message deleted in #{self.bot.get_channel(record.get('channel_id'))}"
                send_payload["footer"] = f"ID: {record.get('message_id')} | {record.get('create_date')}"
                send_payload["author"] = self.bot.get_user(record.get('user_id'))

            else:
                # otherwise we are shit out of luck
                send_payload["panel"] = "Message content was not saved into db or cached"
                send_payload["title"] = f"Message deleted in #{payload.message_id}"
                send_payload["footer"] = f"ID: {payload.message_id}"

        await self.bot.inter_send(
            mod_channel,
            panel=send_payload.get("panel"),
            title=send_payload.get("title"),
            footer=send_payload.get("footer"),
            author=send_payload.get("author"),
            color=EmbedColor.ERROR
        )


def setup(bot):
    bot.add_cog(EventDriver(bot))
