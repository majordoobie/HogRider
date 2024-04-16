from dataclasses import dataclass, field
from datetime import datetime

import disnake


@dataclass
class Language:
    """Represents the LanguageBoard table"""
    role_id: int
    role_name: str
    emoji_id: int
    emoji_repr: str

    def __contains__(self, key: int) -> bool:
        return self.role_id == key


@dataclass
class MemberLanguage(Language):
    """Represents the languages tha a user has"""
    role: disnake.Role
    present: bool


@dataclass
class Message:
    """Represents the user_message table"""
    message_id: int
    user_id: int
    channel_id: int
    created_date: datetime
    content: str


@dataclass
class ThreadMgr:
    """Represents the thread_manager table"""
    thread_id: int
    user_id: int
    created_date: datetime


@dataclass
class CoCEndPointResponse:
    player_resp: int
    clan_resp: int
    war_resp: int


@dataclass
class CoCEndPointStatus(CoCEndPointResponse):
    check_time: datetime


@dataclass
class DemoChannel:
    channel_id: int
    bot_id: int
    owner_id: int
    creation_date: datetime

    channel_obj: disnake.TextChannel | None
    member_obj: disnake.Member | None
    bot_obj: disnake.Member | None

    channel_present: str = field(init=False)
    member_present: str = field(init=False)
    bot_present: str = field(init=False)

    def __post_init__(self):
        self.channel_present = "👍" if self.channel_obj else "❌"
        self.member_present = "👍" if self.member_obj else "❌"
        self.bot_present = "👍" if self.bot_obj else "❌"
