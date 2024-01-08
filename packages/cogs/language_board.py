from typing import Optional, Union
from logging import getLogger
from pathlib import Path

import disnake
from disnake.ext import commands

from packages.config import guild_ids
from packages.utils import crud, models, utils
from packages.utils.utils import EmbedColor
from packages.views.language_view import LanguageView

PANEL_DIRECTIONS = "Choose your language to receive your language role"
IMAGE_PATH = Path("language_board_image.png")


class LanguageBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gap = "<:gap:823216162568405012>"
        self.log = getLogger(f"{self.bot.settings.log_name}.admin")

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
        await inter.response.defer()
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

        # await inter.send("Done")
        await self.bot.inter_send(inter, "Role added",
                                  color=EmbedColor.SUCCESS)

    @commands.check(utils.is_admin)
    @lang.sub_command(guild_ids=guild_ids())
    async def remove_role(
            self,
            inter: disnake.ApplicationCommandInteraction,
            language: str,
    ) -> None:
        """
        Remove registered languages. This is the only way to edit them

        Parameters
        ----------
        language: The language to remove
        """
        await inter.response.defer()

        self.log.debug(f"Fetching for {language} to delete")
        lang = await crud.language_exists(self.bot.pool, language)
        self.log.debug(f"Fetched {lang}")
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
        await inter.response.defer()
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
        await inter.response.defer()
        role_stats = await self._get_role_stats(inter.guild)
        panel = self._get_roles_panel(role_stats, with_emojis=False)
        await self.bot.inter_send(
            inter,
            title="Role Stats",
            panel=panel
        )

    @commands.slash_command(guild_ids=guild_ids())
    async def get_language_role(
            self,
            inter: disnake.ApplicationCommandInteraction) -> None:
        """
        Request language roles granting you access to help channels for
        that language
        """
        await inter.response.defer(ephemeral=True)
        custom_id = f"{inter.author.id}_LANG"

        langs = await crud.get_languages(self.bot.pool)
        view = LanguageView(self.bot, langs, custom_id)
        self.log.debug(f"Sending `{inter.user}` the language role panel")

        await inter.edit_original_message(
            "Please select the languages you would like to add...",
            view=view)

        def check(select_inter: disnake.MessageInteraction) -> bool:
            return select_inter.component.custom_id == custom_id

        await self.bot.wait_for("dropdown", check=check)

        await inter.edit_original_message(
            "Done",
            view=None)

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
