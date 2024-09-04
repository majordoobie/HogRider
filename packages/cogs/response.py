import asyncio
import logging
import time
from datetime import datetime, timezone
import io

import asyncpg
import aiohttp
import disnake
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

    @tasks.loop(minutes=10)
    async def server_display_update(self):
        records = await crud.get_api_response(self.bot.pool)

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

    @tasks.loop(minutes=10)
    async def response_update(self) -> None:
        response_times = await self.get_response_times()
        if -1 not in response_times:
            await crud.set_api_response(self.bot.pool, *response_times)

    @server_display_update.before_loop
    @response_update.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.response_update.cancel()
        self.server_display_update.cancel()

    async def get_response_times(self) -> list[int]:
        """Cycle through all the endpoints to fetch their response times"""
        tasks = [self.get_response_time(url, next(self.bot.coc_client.http.keys), self.log) for url in END_POINTS]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def get_response_time(url: str, auth_token: str, log: logging.Logger) -> int:
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "authorization": "Bearer {}".format(auth_token),
        }

        start = time.perf_counter_ns()
        stop = -1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE}{url}", headers=header) as resp:
                    if resp.status == 503:
                        log.warn("Cannot retrieve API response times due to maintenance")

                    elif resp.status != 200:
                        log.error(f"Error trying to get {BASE}{url}: {await resp.text()}")

                    else: # status == 200
                        stop = time.perf_counter_ns()

        except Exception as e: 
           log.error(f"Error trying to get {BASE}{url}: {e}")

        if stop != -1:
            # Convert nanoseconds to milliseconds
            stop = int((stop - start) / 1_000_000)
        return stop


    @commands.slash_command(guild_ids=guild_ids())
    async def response_times(self,
                             inter: disnake.ApplicationCommandInteraction) -> None:
        """Display a 24-hour graph for the response times"""
        await inter.response.defer()
        records = await crud.get_api_response_24h(self.bot.pool)

        if len(records) == 0:
            response_times = await self.get_response_times()
            self.log.error("Did not get any columns for resonse_times")

            panel = ("Sorry, not enough historical data to show graph. Here is the current response times:\n"
                     f"`Player:`{response_times[0]}\n"
                     f"`Clan:`{response_times[1]}\n"
                     f"`War:`{response_times[2]}\n")
            await self.bot.inter_send(inter, panel=panel)
            return

        columns = [key for key in records[0].__dict__.keys()]
        df = pd.DataFrame(records, columns=columns)

        # Calculate Q1 and Q3 for each column (excluding 'check_time')
        Q1 = df[['clan_resp', 'player_resp', 'war_resp']].quantile(0.25)
        Q3 = df[['clan_resp', 'player_resp', 'war_resp']].quantile(0.75)

        # Calculate the IQR
        IQR = Q3 - Q1

        # Create a mask for filtering outliers
        mask = ~((df[['clan_resp', 'player_resp', 'war_resp']] < (Q1 - 1.5 * IQR)) | (df[['clan_resp', 'player_resp', 'war_resp']] > (Q3 + 1.5 * IQR))).any(axis=1)

        # Filter the DataFrame using the mask
        df = df[mask].reset_index(drop=True)

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
