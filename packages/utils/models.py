from dataclasses import dataclass
from datetime import datetime


@dataclass
class Language:
    """Represents the LanguageBoard table"""
    role_id: int
    role_name: str
    emoji_id: int
    emoji_repr: str


@dataclass
class Message:
    """Represents the user_message table"""
    message_id: int
    user_id: int
    channel_id: int
    created_at: datetime
    content: str


@dataclass
class ThreadMgr:
    """Represents the thread_manager table"""
    thread_id: int
    user_id: int
    created_date: datetime
