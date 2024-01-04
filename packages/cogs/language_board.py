from typing import Optional, Union
from logging import getLogger
from pathlib import Path

import disnake
from disnake.ext import commands

from packages.config import guild_ids
from packages.utils import crud, models, utils
from packages.utils.utils import EmbedColor

PANEL_DIRECTIONS = "Choose your language to receive your language role"
IMAGE_PATH = Path("language_board_image.png")


class LanguageBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gap = "<:gap:823216162568405012>"
        self.log = getLogger(f"{self.bot.settings.log_name}.admin")

    async def _get_role_obj(self,
                            ctx: Union[commands.Context, int],
                            role_id: int) -> Optional[disnake.Role]:
        """Get role object, otherwise log and return None"""
        if isinstance(ctx, int):
            guild = self.bot.get_guild(ctx)
            role = guild.get_role(role_id)
            return role
        else:
            try:
                return ctx.guild.get_role(role_id)
            except Exception:
                self.bot.logger.exception(f"Could not retrieve role {role_id}")
                print("Could not get role ", role_id)
                return None

    async def _get_emoji_obj(self,
                             ctx: commands.Context,
                             emoji_id: int) -> Optional[disnake.Emoji]:
        """Get emoji object, otherwise log and return None. Docs recommend iteration instead
        of fetching"""
        for emoji in ctx.guild.emojis:
            if emoji.id == emoji_id:
                return emoji
        self.bot.logger.exception(f"Could not retrieve role {emoji_id}")
        return None

    def _get_int_from_string(self, string: str) -> Optional[int]:
        """Cast string object into a integer object"""
        if string.isdigit():
            return int(string)
        else:
            self.bot.logger.error(
                f"User input {string} could not be casted to integer")
            return None

    @staticmethod
    def _get_emoji_from_string(string: str) -> Optional[int]:
        """Extract the emoji ID from the string"""
        emoji_id = string.split(":")[-1].rstrip(">")
        if emoji_id.isdigit():
            return int(emoji_id)
        return None

    @staticmethod
    def _get_emoji_repr(emoji: disnake.Emoji) -> str:
        """Cast emoji object to a discord acceptable print format"""
        return f"<:{emoji.name}:{emoji.id}>"

    async def _get_role_stats(self, guild: disnake.Guild) -> dict:
        """Counts how many users are in each role and returns a dictionary

        Parameters
        ----------
        ctx: commands.Context
            Context is used to access server roles

        Returns
        -------
        dict
            Dictionary containing the stats
                {
                    no_roles: int,
                    "roles": list,
                    "spacing": int,
                    "$sample_role": {
                            "count": int,
                            "emoji_repr: $emoji"
                            }
                }
        """
        # Local constants
        developer_role = "Developer"
        no_roles = "No Roles"
        languages = await crud.get_languages(self.bot.pool)
        include = [language.role_name for language in languages]
        include.append(developer_role)

        # Object that is returned
        role_stats = {
            no_roles: 0,
            "roles": [],
            "records": languages,
            "spacing": 0,
        }
        for member in guild.members:
            member: disnake.Member

            # If user only has @everyone role, consider them as having no roles
            if len(member.roles) == 1:
                role_stats[no_roles] += 1
                continue

            # Iterate over all roles a member has in the guild and increment the counter
            for role in member.roles:
                # Ignore excluded roles
                if role.name not in include:
                    continue

                if role_stats.get(role.name) is None:
                    # Calculate the spacing for printing
                    if len(role.name) > role_stats['spacing']:
                        role_stats['spacing'] = len(role.name)

                    emoji_repr = "🖖"
                    for language in languages:
                        if language.role_id == role.id:
                            emoji_repr = language.emoji_repr

                    role_stats[role.name] = {
                        "count": 1,
                        "emoji": emoji_repr
                    }
                    role_stats['roles'].append(role.name)
                else:
                    role_stats[role.name]['count'] += 1

        # Pop Developer role from list
        # if developer_role in role_stats['roles']:
        #     role_stats['roles'].pop(role_stats['roles'].index(developer_role))

        # Sort and prep for iteration
        role_stats['roles'].sort(key=lambda x: role_stats[x]['count'],
                                 reverse=True)
        role_stats['spacing'] += 2

        return role_stats

    def _get_roles_panel(self,
                         role_stats: dict,
                         with_emojis=True) -> Union[str, disnake.Embed]:
        """Create the panel that is used to display the roles stats

        Parameter
        ---------
        role_stats: dict
            Return dictionary from cls._get_role_stats

        Returns
        -------
        str
            String ready to be printed
        """
        # local constants
        developer_role = "Developer"
        no_roles = "No Roles"
        spacing = role_stats['spacing']

        panel = ""

        # Build the rest of the panel
        if with_emojis:
            if role_stats.get(developer_role):
                panel += f"{self.gap} `{developer_role + ':':<{spacing}} {role_stats.get(developer_role)['count']}`\n"
            panel += f"{self.gap} `{no_roles + ':':<{spacing}} {role_stats.get(no_roles)}`\n\n"
            for role in role_stats['roles']:
                if role == developer_role:
                    continue
                count = role_stats.get(role)['count']
                role_name = f"{role}:"
                emoji = role_stats.get(role)['emoji']
                panel += f"{emoji} `{role_name:<{spacing}} {count}`\n"
                panel += f"{emoji} `{role_name:<{spacing}} {count}`\n"
            return disnake.Embed(
                description=panel,
                color=0x000080
            )

        else:
            if role_stats.get(developer_role):
                panel += f"{developer_role + ':':<{spacing}} {role_stats.get(developer_role)['count']}\n"
            panel += f"{no_roles + ':':<{spacing}} {role_stats.get(no_roles)}\n"
            panel += f"{'-' * (spacing + 4)}\n"
            spacing = role_stats['spacing']
            for role in role_stats['roles']:
                if role == developer_role:
                    continue
                count = role_stats.get(role)['count']
                role_name = f"{role}:"
                panel += f"{role_name:<{spacing}} {count}\n"
            panel = f"```{panel}```"
            return panel

    async def _get_message(self, message_id: int, channel_id: int,
                           guild_id: int) -> Optional[disnake.Message]:
        """Get a message object"""
        guild, channel, message = None, None, None
        try:
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            message: disnake.Message
            message = await channel.fetch_message(message_id)
        except Exception:
            msg = (
                f"Could not find the message object\n"
                f"Guild ID: {guild_id}\n"
                f"Guild obj: {guild}\n"
                f"Channel ID: {channel_id}\n"
                f"Channel obj: {channel}\n"
                f"Message ID: {message_id}\n"
                f"Message obj: {message}\n\n"
            )

            self.bot.logger.error(
                f"User input {msg} could not be casted to integer",
                exc_info=True)
            return None
        return message

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,
                                  payload: disnake.RawReactionActionEvent):

        # Ignore the bot
        if payload.member.bot:
            return

        # Ignore if the reaction has nothing to do with the static board
        if payload.message_id != self.bot.stats_board_id:
            return

        # Reset the panel reaction
        message = await self._get_message(payload.message_id,
                                          payload.channel_id, payload.guild_id)
        if message is None:
            return
        await message.remove_reaction(payload.emoji, payload.member)

        # confirm that the reaction is a registered reaction
        async with self.bot.pool.acquire() as conn:
            reaction = await conn.fetch(
                "SELECT role_id, role_name FROM bot_language_board WHERE emoji_id = $1",
                payload.emoji.id)
            if len(reaction) == 1:
                reaction = reaction[0]
            else:
                self.bot.logger.error(
                    f"Returned multiple database records with emoji id of {payload.emoji.id}")
        if not reaction:
            return

        member: disnake.Member = payload.member
        member_roles = member.roles
        remove_role = False

        # Check if this operation is a add or remove
        for role in member_roles:
            if role.id == reaction['role_id']:
                remove_role = True

        # Remove role if user already  has the role
        if remove_role:
            new_roles = []
            for role in member_roles:
                if role.id != reaction['role_id']:
                    new_roles.append(role)
            try:
                await member.edit(roles=new_roles)
            except disnake.Forbidden:
                self.bot.logger.error(
                    f"Could not add {reaction['role_name']} to {member.display_name}",
                    exc_info=True)

        # Otherwise add the role
        else:
            role = await self._get_role_obj(payload.guild_id,
                                            reaction['role_id'])
            try:
                await member.add_roles(role)
            except disnake.Forbidden:
                self.bot.logger.error(
                    f"Could not add {reaction['role_name']} to {member.display_name}",
                    exc_info=True)

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def language_board(self, ctx):
        """
        Create a reaction based panel that gives users roles when they clik on
        the emoji
        """
        # Fetch all the emojis from the database
        async with self.bot.pool.acquire() as conn:
            emojis = await conn.fetch(
                "SELECT emoji_repr FROM bot_language_board")

        # Save the board image to memory
        with IMAGE_PATH.open("rb") as f_handle:
            board_image = disnake.File(f_handle)

        board = await ctx.send(file=board_image)

        # Add the emojis to the panel
        for emoji in emojis:
            await board.add_reaction(emoji['emoji_repr'])

        # Save panel id to memory
        self.bot.stats_board_id = board.id
        self.bot.logger.info(f"Created board with ID: {board.id}")
        await self.bot.pool.execute("UPDATE smelly_mike SET board_id = $1",
                                    self.bot.stats_board_id)

    @commands.check(utils.is_admin)
    @commands.slash_command(guild_ids=guild_ids())
    async def lang(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.check(utils.is_admin)
    @lang.sub_command(guild_ids=guild_ids())
    async def add_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
            role: disnake.Role,
            emoji: disnake.Emoji,
            language: str = commands.Param(converter=utils.to_title),
    ) -> None:
        """
        Register a language and the emoji associated with it

        Parameters
        ----------
        role: The role to register
        emoji: The emoji that represents the role.
        language: Name of the language. Avoid abbreviations.
        """
        if await crud.language_exists(self.bot.pool, role.id):
            await self.bot.inter_send(
                inter,
                panel=(
                    f"Role is already registered. Please list roles and/or "
                    f"remove if you want to change."),
                color=EmbedColor.ERROR
            )
            return

        await crud.set_language(self.bot.pool,
                                models.Language(
                                    role_id=role.id,
                                    role_name=role.name,
                                    emoji_id=emoji.id,
                                    emoji_repr=self._get_emoji_repr(emoji)
                                ))

        self.log.info(
            f"Registered language {language} with "
            f"<{role.name}:{role.id}> : {emoji}")
        await self.bot.inter_send(inter, "Role added",
                                  color=EmbedColor.SUCCESS)

    @commands.check(utils.is_admin)
    @lang.sub_command(guild_ids=guild_ids())
    async def remove_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
            language: str = commands.Param(converter=utils.to_title),
    ) -> None:
        """
        Remove registered languages. This is the only way to edit them

        Parameters
        ----------
        language: The language to remove
        """
        lang = await crud.language_exists(self.bot.pool, language)
        if lang:
            await crud.del_language(self.bot.pool, lang.role_id)

            await self.bot.inter_send(
                inter,
                panel=f"Language {language} has been removed",
                color=EmbedColor.SUCCESS
            )

        else:
            await self.bot.inter_send(
                inter,
                panel=f"Unable to remove {language}",
                color=EmbedColor.ERROR
            )

    @commands.check(utils.is_admin)
    @lang.sub_command(guild_ids=guild_ids())
    async def list_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
    ) -> None:
        """
        List the registered languages
        """

        langs = await crud.get_languages(self.bot.pool)
        panel = f"{'Role':<30} {'Emoji'}\n"
        for lang in langs:
            panel += f"`{lang.role_name:<15}` {lang.emoji_repr}\n"

        await self.bot.inter_send(inter, panel=panel)

    @commands.slash_command(guild_ids=guild_ids())
    async def role_stats(self,
                         inter: disnake.ApplicationCommandInteraction):
        """
        List how many users have each language role
        """

        role_stats = await self._get_role_stats(inter.guild)
        panel = self._get_roles_panel(role_stats, with_emojis=False)
        await self.bot.inter_send(
            inter,
            title="Role Stats",
            panel=panel
        )

    @remove_role.autocomplete("language")
    async def language_name_autocmp(
            self,
            inter: Optional[disnake.ApplicationCommandInteraction],
            user_input: str) -> list[str]:
        """
        Autocomplete callback. To add this callback to a function add the
        decorator for the function.

        :param inter: Interaction
        :param user_input: The current input of the user
        :return: List of possible options based on the user input
        """

        langs = await crud.get_languages(self.bot.pool)

        return [lang.role_name for lang in langs if
                user_input.title() in lang.role_name]


def setup(bot):
    bot.add_cog(LanguageBoard(bot))
