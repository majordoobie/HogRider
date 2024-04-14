import asyncio
import logging
import time

import requests
from disnake.ext import commands, tasks

from bot import BotClient
from packages.utils import crud, models, utils

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

        self.response_update.start()
        self.server_display_update.start()

    @tasks.loop(seconds=30)
    async def server_display_update(self):
        records = await crud.get_api_response(self.bot.pool)

        for key_name in records.__dict__.keys():
            channel = self.bot.get_channel(self.bot.settings.get_channel(key_name))
            if channel is None:
                self.log.error(f"Could not find channel {key_name}")
                continue

            channel_name = " ".join(key_name.split("_")).title()
            await channel.edit(name=f"{channel_name}: {records.__dict__.get(key_name)}ms")

    @tasks.loop(seconds=15)
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


def setup(bot):
    bot.add_cog(Response(bot))
