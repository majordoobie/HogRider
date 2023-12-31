from typing import TYPE_CHECKING

import disnake

from asyncpg import Record

if TYPE_CHECKING:
    from bot import BotClient


class LanguageSelector(disnake.ui.View):
    def __init__(self, bot: "BotClient", lang_records: list[Record]) -> None:
        super().__init__(timeout=60 * 5)
        self.bot = bot
        self.selection = LanguageDropdown(bot, lang_records)
        self.add_item(self.selection)

    async def on_timeout(self) -> None:
        """Clear the panel on timeout"""
        self.remove_item(self.selection)


class LanguageDropdown(disnake.ui.StringSelect):
    def __init__(self, bot: "BotClient", lang_records: list[Record]) -> None:
        options = []
        for lang in lang_records:
            options.append(disnake.SelectOption(
                label=lang.get("role_name"),
                emoji=lang.get("emoji_repr"),
                value=lang.get("role_id")))

        super().__init__(
            custom_id="Select Row",
            placeholder="Choose your languages",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.send_message(
            f"Your favorite type of animal is: {self.values[0]}")


# class HappyDropdown(disnake.ui.Select):
#     def __init__(self, bot: BotClient, emojis: List[str]):
#         self.bot = bot
#         self.emojis = emojis
#
#         options = []
#         for emoji in emojis:
#             options.append(disnake.SelectOption(
#                 label=emoji,
#                 emoji=EMOJIS[emoji]))
#         super().__init__(
#             placeholder="Choose a donation zone...",
#             min_values=1,
#             max_values=len(options),
#             options=options,
#         )
#
#     async def stop_panel(self,
#                          message: disnake.Message,
#                          record: asyncpg.Record,
#                          ) -> None:
#         """
#         Stop a panel from running and remove the selection box
#
#         :param message: Message object to edit
#         :param inter: Inter object to send to
#         :param record: The record of the panel
#         """
#         record = dict(record)
#         record["active"] = False
#         await _refresh_panel(record, self.bot, message, kill=True)
#         sql = "UPDATE happy SET active=$1 WHERE panel_name=$2"
#         async with self.bot.pool.acquire() as con:
#             await con.execute(sql, False, record['panel_name'])
#
#     async def callback(self, inter: disnake.MessageInteraction):
#         async with self.bot.pool.acquire() as con:
#             sql = "SELECT * FROM happy WHERE message_id=$1"
#             record = await con.fetchrow(sql, inter.message.id)
#
#         if "Stop" in self.values or record["active"] == False:
#             await self.stop_panel(inter.message, record)
#             return
#
#         for opt in self.values:
#             if record["data"][opt] is not None:
#                 record["data"][opt] = None
#             else:
#                 record["data"][opt] = inter.user.display_name
#
#         # Update the panel and defer to complete the interaction
#         await _refresh_panel(record, self.bot, inter.message)
#         await inter.response.defer()
#
#         # Update the database
#         async with self.bot.pool.acquire() as con:
#             sql = "UPDATE happy SET data=$1 WHERE panel_name=$2"
#             await con.execute(sql, record["data"], record["panel_name"])
#
#         # Automatically remove reactions when panel is full
#         done = True
#         for index, value in enumerate(record["data"].values()):
#             if index >= record["panel_rows"]:
#                 continue
#             if value is None:
#                 done = False
#         if record["data"]["Top-off"] is None:
#             done = False
#         if record["data"]["Super Troop"] is None:
#             done = False
#
#         # If done, remove reactions and set panel to false
#         if done:
#             await self.stop_panel(inter.message, record)
