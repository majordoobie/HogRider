import coc.utils
import discord
import re
from discord import Interaction, ui
from discord.ext import commands

SECTION_MATCH = re.compile(
    r'(?P<title>.+?)<a name="(?P<number>\d+|\d+.\d+)"></a>(?P<body>(.|\n)+?(?=(#{2,3}|\Z)))')
UNDERLINE_MATCH = re.compile(r"<ins>|</ins>")
URL_EXTRACTOR = re.compile(r"\[(?P<title>.*?)\]\((?P<url>[^)]+)\)")


class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: discord.ButtonStyle, *,
                 custom_id: str):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=10.0)
        self.value = None
        self.add_item(ConfirmButton("Yes", discord.ButtonStyle.green,
                                    custom_id="confirm_button"))
        self.add_item(ConfirmButton("No", discord.ButtonStyle.red,
                                    custom_id="decline_button"))


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        welcome_channel = self.bot.settings.get_channel("welcome")
        if message.channel.id == welcome_channel and message.type is discord.MessageType.thread_created:
            await message.delete(delay=5)

    @discord.slash_command(name="invite")
    async def invite(self, interaction: discord.Interaction):
        """Responds with the invite link to this server"""
        await interaction.response.send_message("https://discord.gg/clashapi")

    @discord.slash_command(name="regex")
    async def regex(self, interaction: discord.Interaction):
        """Responds with the RegEx for player/clan tags"""
        await interaction.response.send_message("^#[PYLQGRJCUV0289]{3,9}$")

    @discord.slash_command(name="rate_limit")
    async def rate_limit(self, interaction: discord.Interaction):
        """Responds with the rate limit information for the Clash API"""
        print("preparing to respond")
        await interaction.response.send_message(
            "We have found that the approximate rate limit is 30-40 requests per "
            "second. Staying below this should be safe.")
        print("done responding")

    @discord.slash_command(name="cache_max_age")
    async def refresh_interval(self, interaction: discord.Interaction):
        """Responds with the max age of the information for each endpoint in the ClashAPI"""
        embed = discord.Embed(title="Max age of information due to caching")
        embed.add_field(name="Clans", value="2 Minutes", inline=False)
        embed.add_field(name="current war", value="2 Minutes", inline=False)
        embed.add_field(name="All other war related", value="10 Minutes",
                        inline=False)
        embed.add_field(name="Player", value="1 Minute", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.slash_command(name="vps")
    async def vps(self, interaction: discord.Interaction):
        """Responds with a link to a GitHub MD on VPS options"""
        await interaction.response.send_message(
            "<https://github.com/wpmjones/apibot/blob/master/Rules/vps_services.md>")

    @discord.slash_command(name="rules")
    async def rules(self, interaction: discord.Interaction):
        """Respond with a link to the rules markdown file."""
        await interaction.response.send_message(
            "<https://github.com/wpmjones/apibot/blob/master/"
            "Rules/code_of_conduct.md>")

    @discord.slash_command(name="links")
    async def link_api(self, interaction: discord.Interaction):
        """Responds with a link to a Discord message on the Discord Link API (by TubaKid)"""
        await interaction.response.send_message(
            "https://discord.com/channels/566451504332931073/681617252814159904/"
            "936126372873650237")

    @discord.slash_command(name="coc_wrappers")
    async def link_coc_wrappers(self, interaction: discord.Interaction):
        """Respond with a link to the page created by @Doluk"""
        await interaction.response.send_message(
            "<https://coc-libs.vercel.app/>")

    @discord.slash_command(name="discord_wrappers")
    async def link_discord_wrappers(self, interaction: discord.Interaction):
        """Respond with a link to a list of known discord wrappers"""
        await interaction.response.send_message("<https://libs.advaith.io/>")

    @discord.slash_command(name="player_url")
    async def format_player_url(self, interaction: discord.Interaction,
                                player_tag: str = ""):
        """Gives info on how to construct a player profile url and optionally the url for a specific player"""
        if player_tag:
            if coc.utils.is_valid_tag(player_tag):
                response = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23" \
                           f"{coc.utils.correct_tag(player_tag, prefix='')}\n\n"
            else:
                response = "I will not construct you a link with an invalid player tag\n\n"
        else:
            response = ""
        response += (
            "You can construct a profile link for any player by combining the following base url with the "
            "player's tag. But make sure to replace the `#` prefix with its encoded form `%23`\n"
            "```https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=```")
        await interaction.response.send_message(response)

    @discord.slash_command(name="help",
                            description="Help command for slash commands")
    async def slash_help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Overview of Slash Commands",
                               color=0xFFFFFF)
        commands: list[
            discord.BaseApplicationCommand] = self.bot.get_all_application_commands()
        global_outside_group = []
        guild_outside_group = []
        global_groups = []
        guild_groups = []
        for cmd in commands:
            # skip all non slash commands
            if cmd.type != discord.ApplicationCommandType(1):
                continue
            # skip admin specific slash commands
            if cmd.qualified_name in ["doobie", "help"]:
                continue
            # get guild specific payload
            payload = cmd.get_payload(
                interaction.guild_id if cmd.guild_ids else None)
            options = payload.get("options", {})
            if all([option['type'] > 2 for option in options]):
                # there is no subcommand or command group
                if cmd.guild_ids:
                    guild_outside_group.append(f"</{cmd.qualified_name}:"
                                               f"{cmd.command_ids[interaction.guild_id]}> "
                                               f"{cmd.description}\n")
                    continue
                else:
                    global_outside_group.append(f"</{cmd.qualified_name}:"
                                                f"{cmd.command_ids[None]}>"
                                                f" {cmd.description}\n")
                    continue
            else:
                # handle subcommand group/ subcommands
                sub_commands = sorted(
                    [f"</{cmd.qualified_name} {option['name']}:"
                     f"{cmd.command_ids[interaction.guild_id if cmd.guild_ids else None]}> "
                     f"{option['description']}" for option in options if
                     option['type'] <= 2],
                    key=lambda x: x)
                if cmd.guild_ids:
                    embed = discord.Embed(
                        title=f'Guild Commands of the {cmd.qualified_name} group [{len(sub_commands)}]',
                        description="\n".join(sub_commands),
                        color=0xDDDDDD
                    )
                    guild_groups.append(embed)
                else:
                    embed = discord.Embed(
                        title=f'Global Commands of the {cmd.qualified_name} group [{len(sub_commands)}]',
                        description="\n".join(sub_commands),
                        color=0xDDDDDD
                    )
                    global_groups.append(embed)
        ungrouped_global = discord.Embed(
            title=f'Global Commands [{len(global_outside_group)}]',
            description="\n".join(
                sorted(global_outside_group, key=lambda x: x)),
            color=0xFFFFFF)
        ungrouped_guild = discord.Embed(
            title=f'Guild Commands [{len(guild_outside_group)}]',
            description="\n".join(
                sorted(guild_outside_group, key=lambda x: x)),
            color=0xFFFFFF)
        embeds = ([ungrouped_global] + list(
            sorted(global_groups, key=lambda x: x.title)) + [ungrouped_guild] +
                  list(sorted(guild_groups, key=lambda x: x.title)))
        await interaction.response.send_message(embeds=embeds)

    @commands.command(name="setup", aliases=["set_up", ], hidden=True)
    @commands.has_role("Admin")
    async def setup_bot(self, ctx, bot: discord.Member = None,
                        owner: discord.Member = None):
        """Admin use only: For adding bot demo channels
        Creates channel (based on bot name)
        Alphabetizes channel within the Bot-Demos category
        Sets proper permissions
        Sets the channel topic to 'Maintained by [owner]'
        Pings owner so they see the channel and can demonstrate features
        Adds the "Bots" role to the bot.

        **Example:**
        //setup @bot @owner

        **Permissions:**
        Admin role required
        """
        if not bot or not owner:
            return await ctx.send(
                "Please be sure to provide a Discord ID or mention both the bot and the owner. "
                "`//setup @bot @owner`")
        if not bot.bot:
            return await ctx.send(
                f"{bot.mention} does not appear to be a bot. Please try again with "
                f"`//setup @bot @owner`.")
        if owner.bot:
            return await ctx.send(
                f"{owner.mention} appears to be a bot, but should be the bot owner. Please try "
                f"again with `//setup @bot @owner`.")

        get_channel_cb = self.bot.settings.get_channel
        get_role_cb = self.bot.settings.get_role

        category = self.bot.settings.bot_demo_category
        guild = self.bot.get_guild(self.bot.settings.guild)
        guest_role = guild.get_role(get_role_cb("guest"))
        developer_role = guild.get_role(get_role_cb("developer"))
        hog_rider_role = guild.get_role(get_role_cb("hog_rider"))
        admin_role = guild.get_role(get_role_cb("admin"))
        channel_name = f"{bot.name}-demo"
        topic = f"Maintained by {owner.display_name}"

        # check for existing bot demo channel before proceeding
        for channel in category.channels:
            if channel_name == channel.name:
                return await ctx.send(
                    "It appears that there is already a demo channel for this bot.")

        # No match found, just keep swimming
        overwrites = {
            bot: discord.PermissionOverwrite(read_messages=True,
                                              send_messages=True,
                                              read_message_history=True,
                                              manage_messages=True,
                                              embed_links=True,
                                              attach_files=True,
                                              external_emojis=True,
                                              add_reactions=True),
            admin_role: discord.PermissionOverwrite(read_messages=True,
                                                     send_messages=True,
                                                     read_message_history=True,
                                                     manage_messages=True,
                                                     embed_links=True,
                                                     attach_files=True,
                                                     external_emojis=True,
                                                     add_reactions=True,
                                                     manage_channels=True,
                                                     manage_permissions=True,
                                                     manage_webhooks=True),
            hog_rider_role: discord.PermissionOverwrite(read_messages=True,
                                                         send_messages=True,
                                                         read_message_history=True,
                                                         manage_messages=True,
                                                         embed_links=True,
                                                         attach_files=True,
                                                         external_emojis=True,
                                                         add_reactions=True),
            developer_role: discord.PermissionOverwrite(read_messages=True,
                                                         send_messages=True,
                                                         read_message_history=True,
                                                         manage_messages=False,
                                                         embed_links=True,
                                                         attach_files=True,
                                                         external_emojis=True,
                                                         add_reactions=True),
            guest_role: discord.PermissionOverwrite(read_messages=True,
                                                     send_messages=True,
                                                     read_message_history=True,
                                                     manage_messages=False,
                                                     embed_links=True,
                                                     attach_files=True,
                                                     external_emojis=False,
                                                     add_reactions=True),
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
        }
        try:
            position = category.channels[0].position + sorted(
                category.channels + [channel_name], key=lambda c: str(c)
            ).index(channel_name)

            channel = await ctx.guild.create_text_channel(channel_name,
                                                          overwrites=overwrites,
                                                          category=category,
                                                          position=position,
                                                          topic=topic,
                                                          reason=f"Created by the setup command of Hog Rider ({ctx.author})",
                                                          )
        except:
            self.bot.logger.exception("Failed creating channel")

        # ping owner
        await channel.send(
            f"{owner.mention} This channel has been set up for your use in demonstrating the features "
            f"of **{bot.name}**. Limited troubleshooting with others is acceptable, but please do not "
            f"allow this channel to become a testing platform.  Thanks!")

        # add the "Bots" role
        await bot.add_roles(ctx.guild.get_role(get_role_cb("bots")),
                            reason=f"Added by setup command of Hog Rider ({ctx.author})",
                            )

        # sort the Bot-Demo channels alphabetically
        for index, channel in enumerate(sorted(category.channels,
                                               key=lambda c: str(c)),
                                        start=category.channels[0].position):
            if channel.position != index:
                await channel.edit(position=index)

        # Provide user feedback on success
        await ctx.message.add_reaction("\u2705")
        await ctx.send(
            f"If {owner.display_name} would like bot monitoring, here's your command:\n"
            f"`//bot add {bot.id}`")

    @discord.slash_command(name="doobie")
    async def clear(self,
                    interaction: discord.Interaction,
                    msg_count: str = discord.SlashOption(
                        description="Message count OR Message ID",
                        required=False)):
        """Clears the specified number of messages OR all messages from the specified ID. (Admin only)

        **Examples:**
        /doobie (will ask for confirmation first)
        /doobie 7 (no confirmation, will delete the 7 previous messages)
        /doobie 1044857124779466812 (no confirmation, will delete all messages up to and including that one)

        **Permissions:**
        Manage Messages
        """
        if msg_count:
            msg_count = int(msg_count)
            if msg_count < 100:
                await interaction.channel.purge(limit=msg_count)
                await interaction.send(f"{msg_count} messages deleted.",
                                       delete_after=5,
                                       ephemeral=True)
            else:
                try:
                    message = await interaction.channel.fetch_message(
                        msg_count)
                    messages = await interaction.channel.history(
                        after=message).flatten()
                    msg_count = len(messages) + 1
                    await interaction.channel.delete_messages(messages)
                    async for message in interaction.channel.history(limit=1):
                        await message.delete()
                    await interaction.send(f"{msg_count} messages deleted.",
                                           delete_after=5,
                                           ephemeral=True)
                except discord.errors.NotFound:
                    return await interaction.send(
                        "It appears that you tried to enter a message ID, but I can't find "
                        "that message in this channel.")
        else:
            confirm_view = ConfirmView()

            def disable_all_buttons():
                for _item in confirm_view.children:
                    _item.disabled = True

            confirm_content = (
                f"Are you really sure you want to remove ALL messages from "
                f"the {interaction.channel.name} channel?")
            msg = await interaction.send(content=confirm_content,
                                         view=confirm_view)
            await confirm_view.wait()
            if confirm_view.value is False or confirm_view.value is None:
                disable_all_buttons()
                await msg.delete()
            else:
                disable_all_buttons()
                await interaction.channel.purge()

    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_rules(self, ctx):
        """Recreate the #rules channel. (Admin only)

        This parses the Rules/code_of_conduct.md markdown file, and sends it as a series of embeds.
        Assumptions are made that each section is separated by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various messages.
        """
        channel = self.bot.get_channel(self.bot.settings.get_channel("rules"))
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
                colour = discord.Colour.blue()

            embeds.append(
                discord.Embed(title=title, description=description.strip(),
                               colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(ui.Button(label=title.replace("#", "").strip(),
                                    url=message.jump_url))
        await channel.send(view=view)
        await ctx.send(
            f"Rules have been recreated. View here <#{self.bot.settings.get_channel('rules')}>")

    @commands.command(hidden=True)
    @commands.has_role("Admin")
    async def recreate_projects(self, ctx):
        """Recreate the #community-projects channel. (Admin only)

        This parses the Rules/community_projects.md markdown file, and sends it as a series of embeds.
        Assumptions are made that each section is separated by <a name="x.x"></a>.

        Finally, buttons are sent with links which correspond to the various messages.
        """
        project_channel_id = self.bot.settings.get_channel("projects")
        channel = self.bot.get_channel(project_channel_id)
        await channel.purge()

        with open("Rules/community_projects.md", encoding="utf-8") as fp:
            text = fp.read()

        sections = SECTION_MATCH.finditer(text)

        embeds = []
        titles = []
        for match in sections:
            description = match.group("body")
            # underlines, dividers
            description = UNDERLINE_MATCH.sub("__", description).replace("---",
                                                                         "")
            raw_title = match.group("title")
            if re.search(URL_EXTRACTOR, raw_title):
                match = re.search(URL_EXTRACTOR, raw_title)
                title = match.group("title")
                url = match.group("url")
            else:
                title = raw_title.replace("#", "").strip()
                url = ""

            colour = discord.Colour.blue()

            embeds.append(discord.Embed(title=title, url=url,
                                         description=description.strip(),
                                         colour=colour))
            titles.append(title)

        messages = [await channel.send(embed=embed) for embed in embeds]

        # create buttons
        view = ui.View()
        for i, (message, title) in enumerate(zip(messages, titles)):
            view.add_item(ui.Button(label=title.replace("#", "").strip(),
                                    url=message.jump_url))
        await channel.send(view=view)
        await ctx.send(
            f"Project list has been recreated. View here <#{project_channel_id}>")


def setup(bot):
    bot.add_cog(General(bot))
