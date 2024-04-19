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
        if record.bot_obj:
            await record.bot_obj.kick(reason="Removing demo bot since channel is being removed")

        payload = ""
        payload += f"Removed {record.bot_obj}" if record.bot_obj else ""
        payload += f"Removed {record.channel_obj}" if record.channel_obj else ""

        panel = await self.bot.inter_send(inter,
                                          title="Action complete",
                                          panel=payload,
                                          color=EmbedColor.SUCCESS,
                                          return_embed=True)
        await msg.edit(content=None, view=None, embed=panel[0][0])

    @commands.check(is_admin)
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

        # TODO: Figure out how to handle this situation
        if user_registrations:
            await self.bot.inter_send(
                inter, panel=f"User already has {len(user_registrations)} registrations. Add a view here",
                color=EmbedColor.WARNING
            )
            return

        category = self.bot.get_channel(self.bot.settings.get_channel("bot_demo"))
        overwrites = category.overwrites

        overwrites[bot] = disnake.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            external_emojis=True,
            add_reactions=True)

        channel = await inter.guild.create_text_channel(
            name=f"{bot.name}-demo",
            category=category,
            topic=f"Maintained by {owner.display_name}",
            position=0,
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


#     try:
#         position = category.channels[0].position + sorted(
#             category.channels + [channel_name], key=lambda c: str(c)
#         ).index(channel_name)
#
#         channel = await ctx.guild.create_text_channel(channel_name,
#                                                       overwrites=overwrites,
#                                                       category=category,
#                                                       position=position,
#                                                       topic=topic,
#                                                       reason=f"Created by the setup command of Hog Rider ({ctx.author})",
#                                                       )
#     except:
#         self.bot.logger.exception("Failed creating channel")
#
#     # ping owner
#     await channel.send(
#         f"{owner.mention} This channel has been set up for your use in demonstrating the features "
#         f"of **{bot.name}**. Limited troubleshooting with others is acceptable, but please do not "
#         f"allow this channel to become a testing platform.  Thanks!")
#
#     # add the "Bots" role
#     await bot.add_roles(ctx.guild.get_role(get_role_cb("bots")),
#                         reason=f"Added by setup command of Hog Rider ({ctx.author})",
#                         )
#
#     # sort the Bot-Demo channels alphabetically
#     for index, channel in enumerate(sorted(category.channels,
#                                            key=lambda c: str(c)),
#                                     start=category.channels[0].position):
#         if channel.position != index:
#             await channel.edit(position=index)
#
#     # Provide user feedback on success
#     await ctx.message.add_reaction("\u2705")
#     await ctx.send(
#         f"If {owner.display_name} would like bot monitoring, here's your command:\n"
#         f"`//bot add {bot.id}`")
#
#

def setup(bot):
    bot.add_cog(DemoBot(bot))


def _make_payload(records: list[models.DemoChannel]) -> str:
    payload = ""
    for count, record in enumerate(records):
        payload += (
            f"{record.channel_obj.jump_url if record.channel_obj else 'No Channel Found'}\n"
            f"`{'Owner':>6}`: {record.member_present} {record.member_obj}\n"
            f"`{'Bot':>6}`: {record.bot_present} {record.bot_obj}\n\n"
        )
    return payload

# class ConfirmButton(disnake.ui.Button[]):
#     def __init__(self, label: str, style: disnake.ButtonStyle, *,
#                  custom_id: str):
#         super().__init__(label=label, style=style, custom_id=custom_id)
#
#     async def callback(self, interaction: disnake.Interaction):
#         self.view.value = True if self.custom_id == f"confirm_button" else False
#         self.view.stop()
#
# class ConfirmView(disnake.ui.View):
#     def __init__(self):
#         super().__init__(timeout=10.0)
#         self.value = None
#         self.add_item(ConfirmButton("Yes", disnake.ButtonStyle.green,
#                                     custom_id="confirm_button"))
#         self.add_item(ConfirmButton("No", disnake.ButtonStyle.red,
#                                     custom_id="decline_button"))

#
# @commands.command(hidden=True)
# @commands.has_role("Admin")
# async def recreate_projects(self, ctx):
#     """Recreate the #community-projects channel. (Admin only)
#
#     This parses the Rules/community_projects.md markdown file, and sends it as a series of embeds.
#     Assumptions are made that each section is separated by <a name="x.x"></a>.
#
#     Finally, buttons are sent with links which correspond to the various messages.
#     """
#     project_channel_id = self.bot.settings.get_channel("projects")
#     channel = self.bot.get_channel(project_channel_id)
#     await channel.purge()
#
#     with open("Rules/community_projects.md", encoding="utf-8") as fp:
#         text = fp.read()
#
#     sections = SECTION_MATCH.finditer(text)
#
#     embeds = []
#     titles = []
#     for match in sections:
#         description = match.group("body")
#         # underlines, dividers
#         description = UNDERLINE_MATCH.sub("__", description).replace("---",
#                                                                      "")
#         raw_title = match.group("title")
#         if re.search(URL_EXTRACTOR, raw_title):
#             match = re.search(URL_EXTRACTOR, raw_title)
#             title = match.group("title")
#             url = match.group("url")
#         else:
#             title = raw_title.replace("#", "").strip()
#             url = ""
#
#         colour = discord.Colour.blue()
#
#         embeds.append(discord.Embed(title=title, url=url,
#                                      description=description.strip(),
#                                      colour=colour))
#         titles.append(title)
#
#     messages = [await channel.send(embed=embed) for embed in embeds]
#
#     # create buttons
#     view = ui.View()
#     for i, (message, title) in enumerate(zip(messages, titles)):
#         view.add_item(ui.Button(label=title.replace("#", "").strip(),
#                                 url=message.jump_url))
#     await channel.send(view=view)
#     await ctx.send(
#         f"Project list has been recreated. View here <#{project_channel_id}>")
