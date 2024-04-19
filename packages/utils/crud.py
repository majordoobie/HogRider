from datetime import datetime

import asyncpg
from asyncpg import Pool
import disnake

from . import models


async def set_language(pool: Pool, language: models.Language) -> None:
    """Add a new language to the database"""
    sql = ("INSERT INTO bot_language_board "
           "(role_id, role_name, emoji_id, emoji_repr) "
           "VALUES ($1, $2, $3, $4)")

    async with pool.acquire() as conn:
        await conn.execute(sql,
                           language.role_id,
                           language.role_name,
                           language.emoji_id,
                           language.emoji_repr
                           )


async def get_languages(pool: Pool) -> list[models.Language]:
    """Returns all the registered languages"""
    async with pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT * FROM bot_language_board;")

    langs = []
    for record in records:
        langs.append(models.Language(**record))

    return langs


async def del_language(pool: Pool, role_id: int) -> None:
    """Remove a language from the database"""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM bot_language_board WHERE role_id = $1",
            role_id)


async def language_exists(pool: Pool,
                          role: int | str) -> models.Language | None:
    """Verify is a language exists in the database. If it does return it"""
    async with pool.acquire() as conn:
        if isinstance(role, int):
            row = await conn.fetchrow(
                "SELECT role_id FROM bot_language_board WHERE role_id = $1",
                role)
        else:
            row = await conn.fetchrow(
                "SELECT role_id FROM bot_language_board WHERE role_name = $1",
                role)

    if row:
        return models.Language(**row)
    else:
        return None


async def set_message(pool: Pool, message: disnake.Message) -> None:
    """
    Logs every message into the database
    Parameters
    ----------
    pool: pool object to the database
    message: disnake message to log
    """
    sql = ("INSERT INTO user_message "
           "(message_id, user_id, channel_id, create_date, content) "
           "VALUES ($1, $2, $3, $4, $5)")

    async with pool.acquire() as conn:
        await conn.execute(sql,
                           message.id,
                           message.author.id,
                           message.channel.id,
                           message.created_at,
                           message.content)


async def get_message(pool: Pool,
                      message_id: int) -> models.Message | None:
    """
    Fetch a message from the database if it exists otherwise return None
    Parameters
    ----------
    pool: pool object to the database
    message_id: id of the message to fetch

    Returns
    -------
    message object or None
    """
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT * FROM user_message WHERE message_id = $1",
            message_id)

    if record:
        return models.Message(**record)


async def set_thread_mgr(pool: Pool,
                         thread_id: int,
                         user_id: int,
                         created_at: datetime) -> None:
    """Log the creation of a new thread with the welcome member id"""
    sql = ("INSERT INTO thread_manager "
           "(thread_id, user_id, created_date) "
           "VALUES ($1, $2, $3)")

    async with pool.acquire() as conn:
        await conn.execute(sql, thread_id, user_id, created_at)

    return None


async def get_thread_mgr(pool: Pool,
                         thread_id: int) -> models.ThreadMgr | None:
    async with pool.acquire() as conn:
        """Fetch a thread manager object from the database"""
        record = await conn.fetchrow(
            "SELECT * FROM thread_manager WHERE thread_id = $1",
            thread_id
        )

    if record:
        return models.ThreadMgr(**record)


async def delete_thread_mgr(pool: Pool, thread_id: int) -> None:
    """Delete the thread manager object"""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM thread_manager WHERE thread_id = $1",
            thread_id)


async def set_api_response(pool: Pool, player_resp: int, clan_resp: int, war_resp: int) -> None:
    sql = ("INSERT INTO coc_api_response "
           "(check_time, clan_resp, player_resp, war_resp) "
           "VALUES ($1, $2, $3, $4)")

    async with pool.acquire() as conn:
        await conn.execute(sql, datetime.now(), player_resp, clan_resp, war_resp)

    return None


async def get_api_response(pool: Pool) -> models.CoCEndPointResponse:
    sql = ("SELECT player_resp, clan_resp, war_resp "
           "FROM coc_api_response "
           "ORDER BY check_time DESC")

    async with pool.acquire() as conn:
        record = await conn.fetchrow(sql)

    return models.CoCEndPointResponse(**record)


async def get_api_response_24h(pool: Pool) -> list[models.CoCEndPointStatus]:
    sql = ("SELECT * FROM coc_api_response "
           "WHERE check_time > now() - INTERVAL  '24 hours' "
           "ORDER BY check_time DESC")

    async with pool.acquire() as conn:
        records = await conn.fetch(sql)

    return [models.CoCEndPointStatus(**record) for record in records]


async def set_demo_channel(pool: Pool,
                           channel_id: int,
                           bot_id: int,
                           owner_id: int) -> None:
    sql = "INSERT INTO demo_channel (channel_id, bot_id, owner_id, creation_date) VALUES ($1, $2, $3, $4)"
    async with pool.acquire() as conn:
        await conn.execute(sql, channel_id, bot_id, owner_id, datetime.now())


async def get_demo_channel(pool: Pool, guild: disnake.Guild) -> list[models.DemoChannel]:
    sql = "SELECT * FROM demo_channel"

    async with pool.acquire() as conn:
        records = await conn.fetch(sql)

    results = []
    for record in records:
        member_obj = guild.get_member(record.get("owner_id"))
        bot_obj = guild.get_member(record.get("bot_id"))
        channel_obj = guild.get_channel(record.get("channel_id"))

        results.append(models.DemoChannel(
            **record,
            member_obj=member_obj,
            bot_obj=bot_obj,
            channel_obj=channel_obj
        ))

    return results


async def get_demo_channel_param(
        pool: Pool,
        guild: disnake.Guild,
        param: disnake.Member | disnake.TextChannel) -> models.DemoChannel | None:
    sql = "SELECT * FROM demo_channel WHERE channel_id = $1 or owner_id = $1 or bot_id = $1"
    async with pool.acquire() as conn:
        record = await conn.fetchrow(sql, param.id)

    if record:
        member_obj = guild.get_member(record.get("owner_id"))
        bot_obj = guild.get_member(record.get("bot_id"))
        channel_obj = guild.get_channel(record.get("channel_id"))

        return models.DemoChannel(
            **record,
            member_obj=member_obj,
            bot_obj=bot_obj,
            channel_obj=channel_obj
        )

    else:
        return None
