import asyncio
import logging

import disnake
from disnake.ext import commands

from bot import BotClient
from packages.config import guild_ids
from packages.utils import crud, models
from packages.utils.utils import is_admin, EmbedColor
from packages.views.comfirm_selection import Confirm, Confirmation


class DemoBot(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot: BotClient = bot
        self.log: logging.Logger = logging.getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

    @commands.check(is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def demo_bot_remove(self,
                              inter: disnake.ApplicationCommandInteraction,
                              owner: disnake.Member | None = None,
                              bot: disnake.Member | None = None,
                              channel: disnake.TextChannel | None = None) -> None:
        """Remove a demo channel and kick the bot. The user will not be kicked."""

        if not any([owner, bot, channel]):
            await self.bot.inter_send(inter, panel="Must supply at least one parameter",
                                      color=EmbedColor.ERROR)
            return

        await inter.response.defer()

        param = next(param for param in [owner, bot, channel] if param is not None)
        if param is None:
            await self.bot.inter_send(inter, panel="Was not able to find a record",
                                      color=EmbedColor.ERROR)
            return

        record = await crud.get_demo_channel_param(self.bot.pool, inter.guild, param)

        view = Confirm(self.bot)
        await self.bot.inter_send(inter,
                                  title="Please confirm that you want to remove the following demo",
                                  panel=_make_payload([record]),
                                  view=view)

        msg = await inter.original_response()

        try:
            await self.bot.wait_for(
                "button_click",
                check=lambda i: i.author.id == inter.user.id,
                timeout=60
            )
        except asyncio.TimeoutError:
            panel = await self.bot.inter_send(inter,
                                              panel="Panel timed out; cancelling...",
                                              color=EmbedColor.WARNING,
                                              return_embed=True)
            await msg.edit(content=None, view=None, embed=panel[0][0])
            return None

        if view.answer == Confirmation.DECLINE:
            panel = await self.bot.inter_send(inter, panel="Okay, I won't", color=EmbedColor.WARNING, return_embed=True)
            await msg.edit(content=None, view=None, embed=panel[0][0])
            return

        # if answer == Accept
        # 1) Remove channel
        if record.channel_obj:
            await record.channel_obj.delete(reason="Demo bot cleanup")

        # 2) Remove bot
        try:
            if record.bot_obj:
                await record.bot_obj.kick(reason="Removing demo bot since channel is being removed")
        except:
            # TODO: Remove after done building the app
            pass

        # 3) Remove role
        if record.member_obj:
            demo_owner = inter.guild.get_role(self.bot.settings.get_role("demo_owner"))
            await record.member_obj.remove_roles(demo_owner)

        # 4) Update the db
        param = record.bot_obj if record.bot_obj else record.channel_obj
        await crud.del_demo_channel(self.bot.pool, param)

        payload = ""
        payload += f"Removed {record.bot_obj}" if record.bot_obj else ""
        payload += f"Removed {record.channel_obj}" if record.channel_obj else ""

        panel = await self.bot.inter_send(inter,
                                          title="Action complete",
                                          panel=payload,
                                          color=EmbedColor.SUCCESS,
                                          return_embed=True)
        await msg.edit(content=None, view=None, embed=panel[0][0])

    @commands.slash_command(guild_ids=guild_ids())
    async def demo_bot_list(self,
                            inter: disnake.ApplicationCommandInteraction) -> None:
        """List the registers users in the demo program"""
        await inter.response.defer()

        records = await crud.get_demo_channel(self.bot.pool, inter.guild)

        payload = _make_payload(records)

        await self.bot.inter_send(
            inter,
            panel=payload,
            author=inter.author,
            footer="Emoji represents if member is present in the server",
        )

    @commands.check(is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def demo_bot_setup(self,
                             inter: disnake.ApplicationCommandInteraction,
                             owner: disnake.Member,
                             bot: disnake.Member) -> None:
        """Register a bot to the demos channel for display"""
        if not await self._verify_input(inter, owner, bot):
            return

        await inter.response.defer()
        records = await crud.get_demo_channel(self.bot.pool, inter.guild)

        user_registrations = []
        for record in records:
            # If the bot already has a channel, exit
            if record.bot_id == bot.id:
                await self.bot.inter_send(
                    inter, panel=f"`{bot}` is already registered to {record.channel_obj.jump_url}",
                    color=EmbedColor.WARNING
                )
                return

            # If the user has a channel; keep count and inform the admin
            if record.owner_id == owner.id:
                user_registrations.append(record)

        if user_registrations:
            await self.bot.inter_send(
                inter, panel=f"User already has {len(user_registrations)} registrations. If "
                             f"we run into this, then have doobie add a feature for it.",
                color=EmbedColor.WARNING
            )
            return

        category = self.bot.get_channel(self.bot.settings.get_channel("bot_demo"))
        overwrites = category.overwrites

        # Add the bot for the demo channel with its own permissions
        overwrites[bot] = disnake.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            external_emojis=True,
            add_reactions=True)

        position = _calculate_position(category, f"{bot.name}-demo")

        channel = await inter.guild.create_text_channel(
            name=f"{bot.name}-demo",
            category=category,
            topic=f"Maintained by {owner.display_name}",
            position=position,
            overwrites=overwrites
        )

        mod_log = self.bot.get_channel(self.bot.settings.get_channel("mod-log"))
        await self.bot.inter_send(
            mod_log,
            panel=f"Created {channel.jump_url} for {owner.mention} to demo their bot {bot.mention}",
            color=EmbedColor.SUCCESS,
            author=inter.author
        )

        await self.bot.inter_send(
            inter, panel=f"Created {channel.jump_url}", color=EmbedColor.SUCCESS,
        )

        await crud.set_demo_channel(self.bot.pool, channel.id, bot.id, owner.id)

        # Add roles
        demo_bot_role = inter.guild.get_role(self.bot.settings.get_role("demo_bot"))
        demo_owner_role = inter.guild.get_role(self.bot.settings.get_role("demo_owner"))
        await bot.add_roles(demo_bot_role)
        await owner.add_roles(demo_owner_role)
        await channel.send(f"Hey {owner.mention}, use this channel to show off your bot!")

    async def _verify_input(self,
                            inter: disnake.ApplicationCommandInteraction,
                            member: disnake.Member,
                            bot: disnake.Member) -> bool:
        if member.bot:
            await self.bot.inter_send(
                inter,
                panel="Member parameter must not be a bot",
                color=EmbedColor.ERROR
            )
            return False

        if not bot.bot:
            await self.bot.inter_send(
                inter,
                panel="Bot parameter must be a bot",
                color=EmbedColor.ERROR
            )
            return False

        return True


def setup(bot):
    bot.add_cog(DemoBot(bot))


def _calculate_position(category: disnake.CategoryChannel, bot_name: str) -> int:
    channel_list = [channel.name for channel in category.channels]
    channel_list.append(bot_name)
    channel_list.sort()
    return channel_list.index(bot_name)


def _make_payload(records: list[models.DemoChannel]) -> str:
    payload = ""
    for count, record in enumerate(records):
        payload += (
            f"{record.channel_obj.jump_url if record.channel_obj else 'No Channel Found'}\n"
            f"`{'Owner':>6}`: {record.member_present} {record.member_obj.mention if record.member_obj else record.owner_id}\n"
            f"`{'Bot':>6}:` {record.bot_present} {record.bot_obj.mention if record.bot_obj else record.bot_id}\n"
            f"`{'Added':>6}:` {record.creation_date.strftime('%Y%m%d %H:%M')}\n\n"
        )
    return payload
