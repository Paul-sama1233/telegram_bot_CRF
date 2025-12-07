# telegram_poster/models/bot.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Bot:
    id: Optional[int] = None
    bot_token: str = ""
    bot_username: str = ""
    bot_name: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'bot_token': self.bot_token,
            'bot_username': self.bot_username,
            'bot_name': self.bot_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            bot_token=data.get('bot_token', ''),
            bot_username=data.get('bot_username', ''),
            bot_name=data.get('bot_name', ''),
            is_active=bool(data.get('is_active', True)),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )