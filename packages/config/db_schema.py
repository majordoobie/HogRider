def init_tables() -> list[str]:
    return [
        _table_create_language_board(),
        _table_create_smelly_mike(),
        _table_create_user_message(),
        _table_create_thread_manager(),
        _table_create_bot_responses(),
    ]


def _table_create_language_board() -> str:
    return """\
        CREATE TABLE IF NOT EXISTS bot_language_board (
            role_id BIGINT PRIMARY KEY,
            role_name TEXT NOT NULL,
            emoji_id BIGINT NOT NULL,
            emoji_repr TEXT NOT NULL
        );
        """


def _table_create_smelly_mike() -> str:
    return """\
        CREATE TABLE IF NOT EXISTS smelly_mike (
            board_id BIGINT NOT NULL,
            PRIMARY KEY(board_id)
        );
    """


def _table_create_user_message() -> str:
    return """\
    CREATE TABLE IF NOT EXISTS user_message (
        message_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        channel_id BIGINT NOT NULL,
        create_date DATE NOT NULL,
        content TEXT,
        PRIMARY KEY(message_id)
    );
    """

def _table_create_thread_manager() -> str:
    return """\
    CREATE TABLE IF NOT EXISTS thread_manager (
        thread_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        created_date DATE NOT NULL,
        PRIMARY KEY (thread_id)
    )
    """

def _table_create_bot_responses() -> str:
    return """\
    CREATE TABLE IF NOT EXISTS coc_api_response (
        check_time TIMESTAMP NOT NULL,
        clan_resp SMALLINT NOT NULL,
        player_resp SMALLINT NOT NULL,
        war_resp SMALLINT NOT NULL
        )
        """
    
