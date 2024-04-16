import asyncio
import logging
import time
from datetime import datetime, timezone
import io

import asyncpg
import disnake
import requests
from disnake.ext import commands, tasks
import pandas as pd
from matplotlib.ticker import NullFormatter

from bot import BotClient
from packages.config import guild_ids, BotMode
from packages.utils import crud

BASE = "https://api.clashofclans.com/v1"
END_POINTS = [
    "/players/%23PJU928JR",
    "/clans/%23CVCJR89",
    "/clans/%23UGJPVJR/currentwar"
]


class Response(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot: BotClient = bot
        self.log: logging.Logger = logging.getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

        if self.bot.settings.mode == BotMode.LIVE_MODE:
            self.response_update.add_exception_type(asyncpg.PostgresConnectionError)
            self.response_update.start()
            self.server_display_update.start()

    @tasks.loop(minutes=5)
    async def server_display_update(self):
        records = await crud.get_api_response(self.bot.pool)
        self.log.debug(f"Response update: Player: {records.player_resp}ms "
                       f"Clan: {records.clan_resp}ms War: {records.war_resp}ms")

        channel = self.bot.get_channel(self.bot.settings.get_channel("resp_update"))
        if channel is not None:
            await channel.edit(name=f"Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S(UTC)')}")

        for key_name in records.__dict__.keys():
            channel = self.bot.get_channel(self.bot.settings.get_channel(key_name))
            if channel is None:
                self.log.error(f"Could not find channel {key_name}")
                continue

            channel_name = " ".join(key_name.split("_")).title()
            await channel.edit(name=f"{channel_name}: {records.__dict__.get(key_name)}ms")

    @tasks.loop(minutes=5)
    async def response_update(self) -> None:
        loop = asyncio.get_event_loop()
        player_resp, clan_resp, war_resp = await loop.run_in_executor(
            None, self.get_response_times)

        await crud.set_api_response(self.bot.pool, player_resp, clan_resp, war_resp)

    @server_display_update.before_loop
    @response_update.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.response_update.cancel()
        self.server_display_update.cancel()

    def get_response_times(self) -> list[int]:
        """
        In a new thread, perform the get requests sequentially to get their execution
        time. The time is what is going to be logged.

        Returns
        -------
        list: List in the order of END_POINTS
        """
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "authorization": "Bearer {}".format(next(self.bot.coc_client.http.keys)),
        }

        response_times = [-1, -1, -1]

        for index, url in enumerate(END_POINTS):
            start = time.perf_counter_ns()
            try:
                requests.get(url=f"{BASE}{url}", headers=header)
            except Exception as e:
                self.log.error(f"Error trying to get {BASE}{url}: {e}")
                continue

            # Convert nanoseconds to milliseconds
            stop = time.perf_counter_ns()
            response_times[index] = int((stop - start) / 1_000_000)

        return response_times

    @commands.slash_command(guild_ids=guild_ids())
    async def response_times(self,
                             inter: disnake.ApplicationCommandInteraction) -> None:
        """Display a 24-hour graph for the response times"""
        await inter.response.defer()
        records = await crud.get_api_response_24h(self.bot.pool)

        columns = [key for key in records[0].__dict__.keys()]
        df = pd.DataFrame(records, columns=columns)

        """The following code was graciously provided by @lukasthaler"""
        # generate plot
        plot = df.plot.line(x='check_time', y=['clan_resp', 'player_resp', 'war_resp'],
                            title='API Latencies', grid=True, xlabel='Last 24 hours', ylabel='Response Time (ms)')

        # customize legend
        _, labels = plot.get_legend_handles_labels()
        plot.legend([f'{el.split("_")[0].title()} Endpoint' for el in labels], loc='upper right')

        # disable xaxis labels
        plot.xaxis.set_major_formatter(NullFormatter())
        plot.xaxis.set_minor_formatter(NullFormatter())

        # enable xaxis grid
        plot.xaxis.grid(visible=True, which='both')

        with io.BytesIO() as img_bytes:
            fig = plot.get_figure()
            fig.savefig(img_bytes, format='png')
            img_bytes.seek(0)
            file = disnake.File(img_bytes, f'{plot.get_title()}.png')
            await inter.send(file=file)


def setup(bot):
    bot.add_cog(Response(bot))
