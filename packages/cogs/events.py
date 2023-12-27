import disnake
from disnake.ext import commands


class EventDriver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = self.bot.settings.guild
        self.get_channel_cb = self.bot.settings.get_channel
        self.get_role_cb = self.bot.settings.get_role

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild.id != self.guild_id:
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


def setup(bot):
    bot.add_cog(EventDriver(bot))
