# telegram_poster/models/template.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json


@dataclass
class Template:
    id: Optional[int] = None
    name: str = ""
    content: str = ""
    buttons: List[Dict[str, str]] = field(default_factory=list)
    media_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_short_content(self, max_length: int = 100):
        """Сокращенный текст для отображения в списке"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'buttons_json': json.dumps(self.buttons),
            'media_path': self.media_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        buttons = json.loads(data.get('buttons_json', '[]'))

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            content=data.get('content', ''),
            buttons=buttons,
            media_path=data.get('media_path'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )