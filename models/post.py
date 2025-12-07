# telegram_poster/models/post.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class Post:
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    channel_id: str = ""
    status: str = "draft"  # draft, scheduled, sent, error
    scheduled_time: Optional[datetime] = None
    sent_time: Optional[datetime] = None
    media_path: Optional[str] = None
    buttons: List[Dict[str, str]] = field(default_factory=list)
    repeat_interval: Optional[str] = None  # daily, weekly, monthly, none
    repeat_count: int = 0
    repeat_until: Optional[datetime] = None
    error_message: Optional[str] = None
    bot_id: Optional[int] = None
    template_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_status_color(self):
        """Цвет статуса для UI"""
        colors = {
            'draft': '#FFA726',  # оранжевый
            'scheduled': '#42A5F5',  # синий
            'sent': '#66BB6A',  # зеленый
            'error': '#EF5350'  # красный
        }
        return colors.get(self.status, '#757575')

    def get_status_text(self):
        """Текст статуса для UI"""
        texts = {
            'draft': 'Черновик',
            'scheduled': 'Запланировано',
            'sent': 'Отправлено',
            'error': 'Ошибка'
        }
        return texts.get(self.status, self.status)

    def get_display_time(self):
        """Время для отображения в UI"""
        if self.sent_time:
            return self.sent_time.strftime("%d.%m.%Y %H:%M")
        elif self.scheduled_time:
            return f"Запланировано: {self.scheduled_time.strftime('%d.%m.%Y %H:%M')}"
        return ""

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'channel_id': self.channel_id,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'sent_time': self.sent_time.isoformat() if self.sent_time else None,
            'media_path': self.media_path,
            'buttons_json': json.dumps(self.buttons),
            'repeat_interval': self.repeat_interval,
            'repeat_count': self.repeat_count,
            'repeat_until': self.repeat_until.isoformat() if self.repeat_until else None,
            'error_message': self.error_message,
            'bot_id': self.bot_id,
            'template_id': self.template_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        buttons = json.loads(data.get('buttons_json', '[]'))

        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            channel_id=data.get('channel_id', ''),
            status=data.get('status', 'draft'),
            scheduled_time=datetime.fromisoformat(data['scheduled_time']) if data.get('scheduled_time') else None,
            sent_time=datetime.fromisoformat(data['sent_time']) if data.get('sent_time') else None,
            media_path=data.get('media_path'),
            buttons=buttons,
            repeat_interval=data.get('repeat_interval'),
            repeat_count=data.get('repeat_count', 0),
            repeat_until=datetime.fromisoformat(data['repeat_until']) if data.get('repeat_until') else None,
            error_message=data.get('error_message'),
            bot_id=data.get('bot_id'),
            template_id=data.get('template_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )