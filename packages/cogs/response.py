import asyncio
import logging
import time

import requests
from disnake.ext import commands, tasks

from bot import BotClient

BASE = "https://api.clashofclans.com/v1"
END_POINTS = [
    "/players/%23PJU928JR",
    "/clans/%23CVCJR89",
    "/clans/%23UGJPVJR/currentwar"
]


class Response(commands.Cog):

    def __init__(self, bot: BotClient):
        self.bot = bot
        self.log = logging.getLogger(f"{self.bot.settings.log_name}.{self.__class__.__name__}")

        self.response_update.start()

    @tasks.loop(seconds=15)
    async def response_update(self) -> None:
        loop = asyncio.get_event_loop()
        player_resp, clan_resp, war_resp = await loop.run_in_executor(
            None, self.get_response_times)

        print(f"Response update: {player_resp} {clan_resp} {war_resp}")

    @response_update.before_loop
    async def before_response_update(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.response_update.cancel()

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
