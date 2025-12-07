# telegram_poster/models/channel.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Channel:
    id: Optional[int] = None
    chat_id: str = ""
    title: str = ""
    username: Optional[str] = None
    type: str = "channel"  # channel, group, private
    bot_id: Optional[int] = None
    is_active: bool = True

    @property
    def display_name(self):
        if self.username:
            return f"@{self.username}"
        return self.title

    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'title': self.title,
            'username': self.username,
            'type': self.type,
            'bot_id': self.bot_id,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            chat_id=data.get('chat_id', ''),
            title=data.get('title', ''),
            username=data.get('username'),
            type=data.get('type', 'channel'),
            bot_id=data.get('bot_id'),
            is_active=bool(data.get('is_active', True))
        )