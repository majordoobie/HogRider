import argparse
import asyncio
import config
import json
from os import getenv

import asyncpg
import coc


def _bot_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process arguments for discord bot")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--live",
        help="Run bot with Panther shell",
        action="store_true",
        dest="live_mode",
        default=False)

    group.add_argument(
        "--dev",
        help="Run in dev shell",
        action="store_true",
        dest="dev_mode",
        default=False)

    return parser.parse_args()


def _get_settings() -> dict:
    args = _bot_args()

    if args.live_mode:
        return config.load_settings("live_mode")
    else:
        return config.load_settings("dev_mode")


async def _get_pool(settings: dict) -> asyncpg.pool.Pool:
    try:
        async def init(con):
            """Create custom column type, json."""
            await con.set_type_codec("json", schema="pg_catalog",
                                     encoder=json.dumps, decoder=json.loads)

        pool = await asyncpg.create_pool(settings["dsn"], init=init)
        return pool
    except Exception as error:
        exit(f"PG error: {error}")


async def _get_coc_client(settings: dict) -> coc.Client:
    coc_client = coc.Client(key_names="APIBOT Keys")
    try:
        await coc_client.login(settings["supercell"]["user"],
                               settings["supercell"]["pass"])
        return coc_client

    except coc.InvalidCredentials as err:
        exit(err)


# def _get_bot_client(settings: Settings, coc_client: coc.EventsClient,
#                     pool: asyncpg.Pool, troop_df: pd.DataFrame) -> BotClient:
#     intents = disnake.Intents.default()
#     intents.message_content = True
#     intents.members = True
#     intents.reactions = True
#     intents.emojis = True
#     intents.guilds = True
#
#     return BotClient(
#         settings=settings,
#         pool=pool,
#         troop_df=troop_df,
#         coc_client=coc_client,
#         command_prefix=settings.bot_config["bot_prefix"],
#         intents=intents,
#         activity=disnake.Game(name=settings.bot_config.get("version")),
#     )
#

async def main(settings: dict) -> None:
    print("Getting Pool")
    pool = await _get_pool(settings)

    print("Getting client")
    coc_client = await _get_coc_client(settings)
    try:
        player = await coc_client.get_player("8CCLPRUQ")
        print(player.name)
    except:
        print("Player not found")

    await coc_client.close()
    await pool.close()
    # # Run the runner function
    # try:
    #     await bot.start(settings.bot_config["bot_token"])
    #
    # except KeyboardInterrupt:
    #     pass  # Ignore interrupts and go to clean up
    #
    # finally:
    #     # Close both pool and client sessions
    #     await pool.close()
    #     await coc_client.close()


if __name__ == "__main__":
    _settings = _get_settings()
    try:
        asyncio.run(main(_settings))
    except KeyboardInterrupt:
        pass
    finally:
        config.save_settings(_settings)

    # # Refresh the sheets on disk
    # clash_stats_levels.download_sheets()
    # troop_df = clash_stats_levels.get_troop_df()
    #
    # # Get bot class
    # print("Getting bot")
    # bot = _get_bot_client(settings, coc_client, pool, troop_df)
    #
    # # Run the runner function
    # try:
    #     await bot.start(settings.bot_config["bot_token"])
    #
    # except KeyboardInterrupt:
    #     pass  # Ignore interrupts and go to clean up
    #
    # finally:
    #     # Close both pool and client sessions
    #     await pool.close()
    #     await coc_client.close()
