from datetime import datetime
import math
import time
import logging

import PIL.ImageDraw
import disnake
from disnake.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import matplotlib.pyplot as plt

from packages.config import guild_ids


class Response(commands.Cog):
    """Cog to check response times for clan, player, and war endpoints and report if things are slow"""

    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.Response")
        self.clan_tag = "CVCJR89"
        self.player_tag = "PJU928JR"
        self.war_tag = "UGJPVJR"  # Not an actual war tag, just a clan we will use to search for wars
        self.response_check.start()

    def cog_unload(self):
        self.response_check.cancel()

    async def fetch_as_dataframe(self, sql) -> pd.DataFrame:
        fetch = await self.bot.pool.fetch(sql)
        columns = [key for key in fetch[0].keys()]
        return pd.DataFrame(fetch, columns=columns)

    async def get_response_times(self):

        # clan endpoint
        start = time.perf_counter()
        await self.bot.coc_client.get_clan(self.clan_tag)
        clan_elapsed_time = (time.perf_counter() - start) * 1000

        # player endpoint
        start = time.perf_counter()
        await self.bot.coc_client.get_player(self.player_tag)
        player_elapsed_time = (time.perf_counter() - start) * 1000

        # current war endpoint
        start = time.perf_counter()
        await self.bot.coc_client.get_clan_war(self.war_tag)
        war_elapsed_time = (time.perf_counter() - start) * 1000

        return clan_elapsed_time, player_elapsed_time, war_elapsed_time

    @commands.slash_command(guild_ids=guild_ids())
    async def response_info(self,
                            inter: disnake.ApplicationCommandInteraction) -> None:
        """Report information on api response times (last 24 hours)"""

        # Get current response times
        clan, player, war = await self.get_response_times()

        # Get historical data from database
        sql = ("SELECT check_time, clan_response, player_response, war_response FROM bot_responses "
               "WHERE check_time > NOW() - interval  '24 hours'"
               "ORDER BY check_time DESC")

        await inter.response.defer()

        df = await self.fetch_as_dataframe(sql)

        col1 = df['clan_response']
        col2 = df['player_response']
        col3 = df['war_response']
        # deal with outliers (greater than 250)
        max_clan_index = max_player_index = max_war_index = 0
        max_clan = max_player = max_war = 250
        if col1.max() > 250:
            max_clan_index = col1.idxmax()  # Get index of max value
            max_clan = col1.max()  # store max value
        if col2.max() > 250:
            max_player_index = col2.idxmax()
            max_player = col2.max()
        if col3.max() > 250:
            max_war_index = col3.idxmax()
            max_war = col3.max()

        y_axis_max = 1500  # Temporary static max
        fig, ax = plt.subplots(figsize=(18, 9))
        ax.set_ylim([0, y_axis_max])
        ax.plot(df['check_time'], df['clan_response'])
        ax.plot(df['check_time'], df['player_response'])
        ax.plot(df['check_time'], df['war_response'])
        if max_clan > y_axis_max:  # if max value is higher than
            ax.text(df['check_time'][max_clan_index],  # the max of y axis add a label for
                    y_axis_max - 15,  # the category (outlier)
                    f"{round_half_up(max_clan, decimals=2)}ms",
                    horizontalalignment="center",
                    fontsize="x-large",
                    color="b")
        if max_player > y_axis_max:
            ax.text(df['check_time'][max_player_index],
                    y_axis_max - 25,
                    f"{round_half_up(max_player, decimals=2)}ms",
                    horizontalalignment="center",
                    fontsize="x-large",
                    color="tab:orange")
        if max_war > y_axis_max:
            ax.text(df['check_time'][max_war_index],
                    y_axis_max - 35,
                    f"{round_half_up(max_war, decimals=2)}ms",
                    horizontalalignment="center",
                    fontsize="x-large",
                    color="g")

        ax.set(xlabel="Last 24 hours", ylabel="Response Time (ms)")
        ax.legend(["Clan Endpoint", "Player Endpoint", "War Endpoint"])
        ax.grid()
        ax.set_xticklabels([])
        fig.savefig("plot.png")

        # prep data for display
        large_font = ImageFont.truetype("fonts/DejaVuSansMono-Bold.ttf", 54)
        small_font = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 24)

        img = Image.new("RGB", (1920, 1080), "white")
        draw = ImageDraw.Draw(img)

        plot_img = Image.open("plot.png")
        img.paste(plot_img, (60, 175))
        status_color = (15, 100, 15)  # Green
        status_text = "All is well"
        if clan > 1000 or player > 1000 or war > 1000:
            status_color = (215, 180, 0)
            status_text = "Minor Slowdown"
        if clan > 2000 or player > 2000 or war > 2000:
            status_color = (100, 15, 15)
            status_text = "There is a problem!"

        draw.rectangle([50, 50, 1870, 150], fill=status_color)

        align(draw, "center", status_text, large_font, (240, 240, 240), (960, 95))
        align(draw, "left", f"Clan Endpoint: {round_half_up(clan, decimals=2)}ms", small_font, (15, 15, 15), (60, 175))
        align(draw, "center",
              f"Player Endpoint: {round_half_up(player, decimals=2)}ms",
              small_font,
              (15, 15, 15),
              (960, 175))
        align(draw, "right", f"War Endpoint: {round_half_up(war, decimals=2)}ms", small_font, (15, 15, 15), (1860, 175))
        img.save("status.png")

        await inter.send(file=disnake.File("status.png"), embed=disnake.Embed(), ephemeral=True)

    @tasks.loop(minutes=15.0)
    async def response_check(self):
        """Task for monitoring coc API response times"""
        # Don't execute if not on production server
        # TODO: Enable this
        # if self.bot.settings.mode != BotMode.LIVE_MODE:
        #     return

        conn = self.bot.pool
        clan_list = []
        player_list = []
        war_list = []
        for _ in range(5):
            c, p, w = await self.get_response_times()
            clan_list.append(c)
            player_list.append(p)
            war_list.append(w)
        clan = sum(clan_list) / len(clan_list)
        player = sum(player_list) / len(player_list)
        war = sum(war_list) / len(war_list)
        sql = ("INSERT INTO bot_responses (check_time, clan_response, player_response, war_response) "
               "VALUES ($1, $2, $3, $4)")
        await conn.execute(sql, datetime.utcnow(), clan, player, war)

        # Update voice channel name
        sql = ("with s as "
               "(SELECT player_response, clan_response, war_response FROM bot_responses "
               "ORDER BY check_time DESC LIMIT $1) "
               "SELECT AVG(player_response) as resp FROM s")
        one_response_time = await conn.fetchrow(sql, 4)
        six_response_time = await conn.fetchrow(sql, 24)
        try:
            channel_id = self.bot.settings.get_channel("api_response")
            channel = self.bot.get_channel(channel_id)
            await channel.edit(name=f"API: {player:.0f}/{one_response_time['resp']:.0f}/"
                                    f"{six_response_time['resp']:.0f}ms")
        except:
            self.log.exception("Channel update failed")

    @response_check.before_loop
    async def before_response_check(self):
        await self.bot.wait_until_ready()


def get_text_dimensions(text: str, font: ImageFont) -> tuple[int, int]:
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text).getbbox()[2]
    text_height = font.getmask(text).getbbox()[3] + descent

    return (text_width, text_height)


def align(draw: PIL.ImageDraw, alignment: str, text: str, font: ImageFont, color: tuple, position: tuple) -> None:
    if not isinstance(text, str):
        text = str(text)

    text_width, text_height = get_text_dimensions(text, font)
    if alignment == "center":
        x = position[0] - (text_width / 2)
    elif alignment == "right":
        x = position[0] - text_width
    else:
        x = position[0]
    y = position[1] - (text_height / 2)
    draw.text((x, y), text, fill=color, font=font)


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier + 0.5) / multiplier


def setup(bot):
    bot.add_cog(Response(bot))
