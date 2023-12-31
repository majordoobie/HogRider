import nextcord
import asyncio

from nextcord.ext import commands
from datetime import datetime, timezone, timedelta


class Deleted:
    pass


class MessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = self.bot.settings.guild
        self.get_channel_cb = self.bot.settings.get_channel
        self.get_role_cb = self.bot.settings.get_role

    @commands.Cog.listener()
    async def on_message(self, message):
        welcome_channel = self.get_channel_cb("welcome")
        if message.channel.id == welcome_channel and message.type is nextcord.MessageType.thread_created:
            await message.delete(delay=1)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Deal with edited messages"""
        if before.guild.id != self.guild_id:
            return

        if before.channel.id in [self.get_channel_cb("admin"),
                                 self.get_channel_cb("mod-log")]:
            return

        if before.author.bot:
            return

        embed = nextcord.Embed(
            title=f"Message edited in #{before.channel.name}",
            color=nextcord.Color.blue())
        embed.set_author(name=before.author.name,
                         icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before:", value=before.content[:1022],
                        inline=False)
        embed.add_field(name="After:", value=after.content[:1022],
                        inline=False)
        embed.add_field(name="Message Link:", value=after.jump_url,
                        inline=False)
        embed.set_footer(text=f"ID: {after.id} | {after.edited_at}")
        mod_channel = self.bot.get_channel(self.get_channel_cb("mod-log"))
        await mod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Deal with deleted messages"""
        if message.guild.id != self.guild_id:
            return
        guild = self.bot.get_guild(self.guild_id)
        if message.channel.id in [self.get_channel_cb("admin"),
                                  self.get_channel_cb("mod-log")]:
            return

        if message.author.bot:
            return

        now_tz = datetime.now().replace(tzinfo=timezone.utc)

        await asyncio.sleep(
            1)  # not sure if this is needed, just giving audit log time to create
        deleted_by = "Message author or someone else (still testing)"
        async for entry in guild.audit_logs(
                action=nextcord.AuditLogAction.message_delete, limit=1):
            if entry.created_at > now_tz - timedelta(
                    seconds=15):  # did delete happen recently
                deleted_by = entry.user.name
        embed = nextcord.Embed(color=nextcord.Color.red())
        embed.set_author(name=message.author.name,
                         icon_url=message.author.display_avatar.url)
        embed.add_field(name=f"Message deleted in #{message.channel.name}",
                        value=message.content[:1022])
        embed.set_footer(text=f"ID: {message.id} | Deleted by: {deleted_by}")
        mod_channel = self.bot.get_channel(self.get_channel_cb("mod-log"))
        await mod_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MessagesCog(bot))
