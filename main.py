import argparse
import asyncio
import json
import logging

import asyncpg
import coc
import disnake

from bot import ApiBot
from config import Settings, BotMode, init_tables, load_settings
from packages.utils.logging_setup import BotLogger


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


def _get_settings() -> Settings:
    args = _bot_args()

    if args.live_mode:
        return load_settings(BotMode.LIVE_MODE)
    else:
        return load_settings(BotMode.DEV_MODE)


async def _get_pool(settings: Settings) -> asyncpg.pool.Pool:
    try:
        async def init(con):
            """Create custom column type, json."""
            await con.set_type_codec("json", schema="pg_catalog",
                                     encoder=json.dumps, decoder=json.loads)

        pool = await asyncpg.create_pool(settings.dsn, init=init)
        async with pool.acquire() as con:
            for table in init_tables():
                await con.execute(table)

        return pool
    except Exception:
        log.critical("Pool error", exc_info=True)


async def _get_coc_client(settings: Settings) -> coc.Client:
    coc_client = coc.Client(key_names="APIBOT Keys")
    try:
        await coc_client.login(settings.coc_email, settings.coc_password)
        return coc_client

    except coc.InvalidCredentials as err:
        log.critical("CoC error", exc_info=True)


def _get_bot_client(settings: Settings, coc_client: coc.Client,
                    pool: asyncpg.Pool) -> ApiBot:
    intents = disnake.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.reactions = True
    intents.emojis = True
    intents.guilds = True

    return ApiBot(
        settings=settings,
        coc_client=coc_client,
        pool=pool,
        intents=intents
    )


async def main(settings: Settings) -> None:
    pool = await _get_pool(settings)
    coc_client = await _get_coc_client(settings)
    log.debug("Bot initialized, starting bot...")
    bot = _get_bot_client(settings, coc_client, pool)

    try:
        await bot.start(settings.bot_token)

    except KeyboardInterrupt:
        pass  # Ignore interrupts and go to clean up

    finally:
        # Close both pool and client sessions
        await pool.close()
        await coc_client.close()


if __name__ == "__main__":
    _settings = _get_settings()
    try:
        BotLogger(_settings)
    except Exception as error:
        exit(error)

    log = logging.getLogger(f"{_settings.log_name}.Main")

    try:
        asyncio.run(main(_settings))
    except KeyboardInterrupt:
        pass
