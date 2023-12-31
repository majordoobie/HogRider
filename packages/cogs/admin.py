import logging
import string
import re
from random import choice, randint

import disnake
from disnake.ext import commands

from packages.utils import utils
from packages.config import guild_ids
from bot import BotClient

SECTION_MATCH = re.compile(
    r'(?P<title>.+?)<a name="(?P<number>\d+|\d+.\d+)"></a>(?P<body>(.|\n)+?(?=(#{2,3}|\Z)))')
UNDERLINE_MATCH = re.compile(r"<ins>|</ins>")
URL_EXTRACTOR = re.compile(r"\[(?P<title>.*?)\]\((?P<url>[^)]+)\)")


# TODO: Enable this feature once discord migration is up and running
# from cogs.archive import chat_exporter


class Admin(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.admin")

    @commands.command(name="lg", hidden=True)
    async def links_get(self, ctx, tag):
        """Get info from links api"""
        if tag.startswith("#"):
            payload = await self.bot.links.get_link(tag)
        else:
            payload = await self.bot.links.get_linked_players(tag)
        return await ctx.send(payload)

    # @commands.command(name="archive")
    # @commands.has_role("Admin")
    # async def archive_channel(self, ctx, limit: int = None):
    #     """Create html file with a transcript of the channel (Admin only)"""
    #     transcript = await chat_exporter.export(ctx.channel, limit=limit,
    #                                             bot=self.bot)
    #     if transcript is None:
    #         return await ctx.send("Nothing to export")
    #     transcript_file = discord.File(io.BytesIO(transcript.encode()),
    #                                    filename=f"transcript-{ctx.channel.name}.html"
    #                                    )
    #     await ctx.send(file=transcript_file)

    @commands.command(name="add_user", hidden=True)
    @commands.is_owner()
    async def add_user(self, ctx, usr):
        """Add user for coc discord links api (owner only)"""
        PUNCTUATION = "!@#$%^&*"
        pwd = choice(string.ascii_letters) + choice(PUNCTUATION) + choice(
            string.digits)
        characters = string.ascii_letters + PUNCTUATION + string.digits
        pwd += "".join(choice(characters) for x in range(randint(8, 12)))
        sql = "INSERT INTO coc_discord_users (username, passwd) VALUES ($1, $2)"
        await self.bot.pool.execute(sql, usr, pwd)
        await ctx.send(
            f"User: {usr} has been created with the following password:")
        await ctx.send(pwd)

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def logout(self, ctx):
        """
        Kill the bot. Only use this if the bot is doing something insane.
        """
        self.log.error('Closing connections...')
        await self.bot.send(ctx, "Logging off")
        try:
            await self.bot.coc_client.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

        try:
            await self.bot.pool.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

        try:
            await self.bot.close()
        except Exception as error:
            self.log.critical("Could not close coc connection", exc_info=True)

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def load_module(self, ctx, module: str):
        """
        Load a module into the running bot

        Parameters
        ----------
        module
            The module to load.
        """
        print(module)
        cog = f"{self.bot.settings.cog_path}.{module}"
        print(cog)
        try:
            self.bot.load_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module load error", exc_info=True)
            return
        await ctx.send(f"Loaded {cog} successfully")
        self.log.debug(f"Loaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def unload_cog(self, ctx, module: str):
        """
        Unload a module from the running bot.

        Parameters
        ----------
        module
            The module to unload
        """
        cog = f"{self.bot.settings.cog_path}.{module}"
        try:
            self.bot.unload_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module unload error", exc_info=True)
            return
        await ctx.send(f"Unloaded {cog} successfully")
        self.log.debug(f"Unloaded {cog} successfully")

    @commands.check(utils.is_owner)
    @commands.slash_command(guild_ids=guild_ids())
    async def reload(self, ctx, module: str):
        """
        Reload a module from the running bot

        Parameters
        ----------
        module
            The module to reload
        """
        cog = f"{self.bot.settings.cog_path}.{module}"

        try:
            self.bot.reload_extension(cog)
        except Exception as error:
            await ctx.send(error)
            self.log.error("Module reload error", exc_info=True)
            return
        await ctx.send(f"Reloaded {cog} successfully")
        self.log.debug(f"Reloaded {cog} successfully")

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def list_cogs(self, ctx):
        """
        List the loaded modules
        """
        output = ''
        for i in self.bot.settings.cogs_list:
            output += f"+ {i.split('.')[-1]}\n"
        await self.bot.send(ctx, output)

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def recreate_rules(self,
                             inter: disnake.ApplicationCommandInteraction):
        """Recreate the #rules channel. (Admin only)


        Note
        -----
        This parses the Rules/code_of_conduct.md markdown file, and sends it
        as a series of embeds. Assumptions are made that each section is separated
        by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various
        messages.
        """
        await inter.response.defer()

        channel = self.bot.get_channel(
            self.bot.settings.get_channel("testing"))
        await channel.purge()

        with open("Rules/code_of_conduct.md", encoding="utf-8") as fp:
            text = fp.read()

        sections = SECTION_MATCH.finditer(text)

        embeds = []
        titles = []
        for match in sections:
            description = match.group("body")
            # underlines, dividers, bullet points
            description = UNDERLINE_MATCH.sub("__", description).replace("---",
                                                                         "").replace(
                "-", "\u2022")
            title = match.group("title").replace("#", "").strip()

            if "." in match.group("number"):
                colour = 0xBDDDF4  # lighter blue for sub-headings/groups
            else:
                colour = disnake.Colour.blue()

            embeds.append(
                disnake.Embed(title=title, description=description.strip(),
                              colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = disnake.ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(
                disnake.ui.Button(label=title.replace("#", "").strip(),
                                  url=message.jump_url))

        await channel.send(view=view)
        await inter.edit_original_message(
            f"Rules have been recreated. View here <#{channel.id}>")

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
    #     if not bot or not owner:
    #         return await ctx.send(
    #             "Please be sure to provide a Discord ID or mention both the bot and the owner. "
    #             "`//setup @bot @owner`")
    #     if not bot.bot:
    #         return await ctx.send(
    #             f"{bot.mention} does not appear to be a bot. Please try again with "
    #             f"`//setup @bot @owner`.")
    #     if owner.bot:
    #         return await ctx.send(
    #             f"{owner.mention} appears to be a bot, but should be the bot owner. Please try "
    #             f"again with `//setup @bot @owner`.")
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
    # @discord.slash_command(name="doobie")
    # async def clear(self,
    #                 interaction: discord.Interaction,
    #                 msg_count: str = discord.SlashOption(
    #                     description="Message count OR Message ID",
    #                     required=False)):
    #     """Clears the specified number of messages OR all messages from the specified ID. (Admin only)
    #
    #     **Examples:**
    #     /doobie (will ask for confirmation first)
    #     /doobie 7 (no confirmation, will delete the 7 previous messages)
    #     /doobie 1044857124779466812 (no confirmation, will delete all messages up to and including that one)
    #
    #     **Permissions:**
    #     Manage Messages
    #     """
    #     if msg_count:
    #         msg_count = int(msg_count)
    #         if msg_count < 100:
    #             await interaction.channel.purge(limit=msg_count)
    #             await interaction.send(f"{msg_count} messages deleted.",
    #                                    delete_after=5,
    #                                    ephemeral=True)
    #         else:
    #             try:
    #                 message = await interaction.channel.fetch_message(
    #                     msg_count)
    #                 messages = await interaction.channel.history(
    #                     after=message).flatten()
    #                 msg_count = len(messages) + 1
    #                 await interaction.channel.delete_messages(messages)
    #                 async for message in interaction.channel.history(limit=1):
    #                     await message.delete()
    #                 await interaction.send(f"{msg_count} messages deleted.",
    #                                        delete_after=5,
    #                                        ephemeral=True)
    #             except discord.errors.NotFound:
    #                 return await interaction.send(
    #                     "It appears that you tried to enter a message ID, but I can't find "
    #                     "that message in this channel.")
    #     else:
    #         confirm_view = ConfirmView()
    #
    #         def disable_all_buttons():
    #             for _item in confirm_view.children:
    #                 _item.disabled = True
    #
    #         confirm_content = (
    #             f"Are you really sure you want to remove ALL messages from "
    #             f"the {interaction.channel.name} channel?")
    #         msg = await interaction.send(content=confirm_content,
    #                                      view=confirm_view)
    #         await confirm_view.wait()
    #         if confirm_view.value is False or confirm_view.value is None:
    #             disable_all_buttons()
    #             await msg.delete()
    #         else:
    #             disable_all_buttons()
    #             await interaction.channel.purge()
    #
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


def setup(bot):
    bot.add_cog(Admin(bot))
