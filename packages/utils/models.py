from dataclasses import dataclass
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
