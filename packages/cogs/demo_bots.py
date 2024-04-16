import logging

import disnake
from disnake.ext import commands

from bot import BotClient
from packages.config import guild_ids
from packages.utils import crud, models
from packages.utils.utils import is_admin


class DemoBot(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot: BotClient = bot
        self.log: logging.Logger = logging.getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

    @commands.check(is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def demo_bot_list(self,
                            inter: disnake.ApplicationCommandInteraction) -> None:
        """List the registers users in the demo program"""
        await inter.response.defer()

        records = await crud.get_demo_channel(self.bot.pool, inter.guild)
        for record in records:
            print(record)

    @commands.check(is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def demo_bot_setup(self,
                             inter: disnake.ApplicationCommandInteraction,
                             member: disnake.Member,
                             bot: disnake.Member) -> None:
        """Register a bot to the demos channel for display"""
        pass

    @demo_bot_setup.autocomplete("bot")
    async def bot_name_autocomplete(self,
                                    inter: disnake.ApplicationCommandInteraction,
                                    bot: disnake.Member) -> list[disnake.Member]:

        bots: list[disnake.Member] = []
        for member in inter.guild.members:
            if not member.bot:
                continue
            bots.append(member)
        return bots


# @commands.command(name="setup", aliases=["set_up", ], hidden=True)
# @commands.has_role("Admin")
# async def setup_bot(self, ctx, bot: discord.Member = None,
#                     owner: discord.Member = None):
#     """Admin use only: For adding bot demo channels
#     Creates channel (based on bot name)
#     Alphabetizes channel within the Bot-Demos category
#     Sets proper permissions
#     Sets the channel topic to 'Maintained by [owner]'
#     Pings owner so they see the channel and can demonstrate features
#     Adds the "Bots" role to the bot.
#
#     **Example:**
#     //setup @bot @owner
#
#     **Permissions:**
#     Admin role required
#     """
#
#     get_channel_cb = self.bot.settings.get_channel
#     get_role_cb = self.bot.settings.get_role
#
#     category = self.bot.settings.bot_demo_category
#     guild = self.bot.get_guild(self.bot.settings.guild)
#     guest_role = guild.get_role(get_role_cb("guest"))
#     developer_role = guild.get_role(get_role_cb("developer"))
#     hog_rider_role = guild.get_role(get_role_cb("hog_rider"))
#     admin_role = guild.get_role(get_role_cb("admin"))
#     channel_name = f"{bot.name}-demo"
#     topic = f"Maintained by {owner.display_name}"
#
#     # check for existing bot demo channel before proceeding
#     for channel in category.channels:
#         if channel_name == channel.name:
#             return await ctx.send(
#                 "It appears that there is already a demo channel for this bot.")
#
#     # No match found, just keep swimming
#     overwrites = {
#         bot: discord.PermissionOverwrite(read_messages=True,
#                                           send_messages=True,
#                                           read_message_history=True,
#                                           manage_messages=True,
#                                           embed_links=True,
#                                           attach_files=True,
#                                           external_emojis=True,
#                                           add_reactions=True),
#         admin_role: discord.PermissionOverwrite(read_messages=True,
#                                                  send_messages=True,
#                                                  read_message_history=True,
#                                                  manage_messages=True,
#                                                  embed_links=True,
#                                                  attach_files=True,
#                                                  external_emojis=True,
#                                                  add_reactions=True,
#                                                  manage_channels=True,
#                                                  manage_permissions=True,
#                                                  manage_webhooks=True),
#         hog_rider_role: discord.PermissionOverwrite(read_messages=True,
#                                                      send_messages=True,
#                                                      read_message_history=True,
#                                                      manage_messages=True,
#                                                      embed_links=True,
#                                                      attach_files=True,
#                                                      external_emojis=True,
#                                                      add_reactions=True),
#         developer_role: discord.PermissionOverwrite(read_messages=True,
#                                                      send_messages=True,
#                                                      read_message_history=True,
#                                                      manage_messages=False,
#                                                      embed_links=True,
#                                                      attach_files=True,
#                                                      external_emojis=True,
#                                                      add_reactions=True),
#         guest_role: discord.PermissionOverwrite(read_messages=True,
#                                                  send_messages=True,
#                                                  read_message_history=True,
#                                                  manage_messages=False,
#                                                  embed_links=True,
#                                                  attach_files=True,
#                                                  external_emojis=False,
#                                                  add_reactions=True),
#         guild.default_role: discord.PermissionOverwrite(
#             read_messages=False),
#     }
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
