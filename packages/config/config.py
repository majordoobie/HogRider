import json
from pathlib import Path
from os import environ
from dataclasses import dataclass, field
from enum import Enum
import logging

_config_path = Path(__file__).parent

VERSION = "2.1.0"


class BotMode(Enum):
    LIVE_MODE = 0
    DEV_MODE = 1


def guild_ids() -> list[int]:
    return [566451504332931073]


@dataclass
class Settings:
    mode: BotMode
    conf: dict

    # db
    db_name: str = field(init=False)
    db_user: str = field(init=False)
    db_pass: str = field(init=False)
    db_port: int = field(init=False)
    db_host: int = field(init=False)

    # coc login
    coc_email: str = environ.get("COC_USER", "null")
    coc_password: str = environ.get("COC_PASS", "null")
    coc_key_names: str = field(init=False)

    # Bot pre configs
    bot_log_level: str = field(init=False)
    bot_prefix: str = field(init=False)

    # Logging
    main_log_level: int = logging.DEBUG
    web_log_url: str = environ.get("WEB_LOG", "null")
    web_log_name: str = "HogRider WebHook"
    logging_format: str = (
        "[%(asctime)s]:[%(levelname)s]:[%(name)s]:[Line:%(lineno)d][Func:%(funcName)s]\n"
        "[Path:%(pathname)s]\n"
        "MSG: %(message)s\n"
    )

    def __post_init__(self):
        # Add the IDs for slash commands this will disable their
        # "global command" status for faster refresh

        self.db_name = environ.get("POSTGRES_DB", "null")
        self.db_user = environ.get("POSTGRES_USER", "null")
        self.db_pass = environ.get("POSTGRES_PASSWORD", "null")
        self.owner = self.conf.get("owner", None)
        self.cog_path = "packages.cogs"

        if BotMode.LIVE_MODE == self.mode:
            # version
            self.version = VERSION

            # db
            self.db_host = environ.get("PG_HOST_LIVE", 0)
            self.db_port = environ.get("PG_PORT_LIVE", 0)

            # coc login
            self.coc_key_names = "LIVE_APIBOT"

            # Bot pre configs
            self.bot_log_level = "INFO"
            self.bot_prefix = "//"

            self.bot_token = environ.get("TOKEN_LIVE")

            self.log_name = "HogRider"

        else:
            # version
            self.version = f"BETA_{VERSION}"

            # db
            self.db_host = environ.get("PG_HOST_DEV", 0)
            self.db_port = environ.get("PG_PORT_DEV", 0)

            # coc login
            self.coc_key_names = "DEV_APIBOT"

            # Bot pre configs
            self.bot_log_level = "DEBUG"
            self.bot_prefix = ">"

            self.bot_token = environ.get("TOKEN_DEV")

            self.log_name = "DevShell"

    @property
    def dsn(self) -> str:
        return f"postgres://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def cogs_list(self) -> list[str]:
        if BotMode.LIVE_MODE == self.mode:
            return [
                "admin",
                "event_driver",
                "general",
                "language_board",
                "welcome"
            ]

        else:
            return [
                "admin",
                "event_driver",
                "general",
                "language_board",
                "welcome"
            ]

    @property
    def logs_channel(self) -> int:
        return self.conf["channels"]["logs"]

    @property
    def guild(self) -> int:
        return self.conf["guild"]["junkies"]

    @property
    def bot_demo_category(self) -> int:
        return self.conf["category"]["bot_demo"]

    def get_role(self, role: str) -> int:
        return self.conf["roles"].get(role, None)

    def get_channel(self, channel: str) -> int:
        return self.conf["channels"][self.mode.name].get(channel, None)


def load_settings(mode: BotMode) -> Settings | None:
    with (_config_path / "config.json").open("rt") as infile:
        settings = json.load(infile)

    return Settings(mode=mode, conf=settings)


def save_settings(settings: dict) -> None:
    pass
    # with (_config_path / "config.json").open("w", encoding="utf-8") as infile:
    #     json.dump(settings, infile, ensure_ascii=False, indent=4,
    #               sort_keys=True)
