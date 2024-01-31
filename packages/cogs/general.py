import disnake
from disnake.ext import commands

from packages.config import guild_ids

from bot import BotClient


class General(commands.Cog):
    def __init__(self, bot: BotClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        welcome_channel = self.bot.settings.get_channel("welcome")
        if message.channel.id == welcome_channel and message.type is disnake.MessageType.thread_created:
            await message.delete(delay=5)

    @commands.slash_command(guild_ids=guild_ids())
    async def invite(self, inter: disnake.ApplicationCommandInteraction):
        """Responds with the invite link to this server"""
        await self.bot.inter_send(inter, "https://discord.gg/clashapi")

    @commands.slash_command(guild_ids=guild_ids())
    async def regex(self, inter: disnake.ApplicationCommandInteraction):
        """Responds with the RegEx for player/clan tags"""
        await self.bot.inter_send(inter, "^#[PYLQGRJCUV0289]{3,9}$")

    @commands.slash_command(guild_ids=guild_ids())
    async def rate_limit(self, inter: disnake.ApplicationCommandInteraction):
        """Responds with the rate limit information for the Clash API"""
        await self.bot.inter_send(
            inter,
            "We have found that the approximate rate limit is 30-40 requests "
            "per second. Staying below this should be safe."
        )

    @commands.slash_command(guild_ids=guild_ids())
    async def refresh_interval(self,
                               inter: disnake.ApplicationCommandInteraction):
        """
        Responds with the max age of the information for each endpoint in the
        Clash API
        """
        payload = (f"{'Clans:':<14}`2 minutes`\n"
                   f"{'Current War:':<14}`2 minutes`\n"
                   f"{'Other War:':<14}`10 Minutes`\n"
                   f"{'Players':<14}`1 Minute`\n"
                   )
        await self.bot.inter_send(inter, panel=payload,
                                  title="Max age of information due to caching"
                                  )

    @commands.slash_command(guild_ids=guild_ids())
    async def vps(self, inter: disnake.ApplicationCommandInteraction):
        """Responds with a link to a GitHub MD on VPS options"""
        await self.bot.inter_send(
            inter,
            "<https://github.com/majordoobie/HogRider/blob/main/Rules/vps_services.md>")

    @commands.slash_command(guild_ids=guild_ids())
    async def rules(self, inter: disnake.ApplicationCommandInteraction):
        """Respond with a link to the rules markdown file."""
        await self.bot.inter_send(
            inter,
            "<https://github.com/wpmjones/apibot/blob/master/Rules/code_of_conduct.md>"
        )

    @commands.slash_command(guild_ids=guild_ids())
    async def getting_started(self, inter: disnake.ApplicationCommandInteraction):
        """
        Respond with a link to the getting started markdown
        """
        await self.bot.inter_send(
            inter,
            "https://github.com/majordoobie/HogRider/blob/main/Rules/getting_started.md"
        )

    @commands.slash_command(guild_ids=guild_ids())
    async def coc_wrappers(self,
                           inter: disnake.ApplicationCommandInteraction):
        """Provide link to the list of coc_wrappers created by @Doluk"""
        await self.bot.inter_send(
            inter,
            "<https://coc-libs.vercel.app/>"
        )

    @commands.slash_command(guild_ids=guild_ids())
    async def discord_wrappers(self,
                               inter: disnake.ApplicationCommandInteraction):
        """Respond with a link to a list of known discord wrappers"""
        await self.bot.inter_send(
            inter,
            "<https://libs.advaith.io/>"
        )


def setup(bot):
    bot.add_cog(General(bot))
