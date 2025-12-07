# telegram_poster/models/__init__.py
from .bot import Bot
from .channel import Channel
from .post import Post
from .template import Template

__all__ = ['Bot', 'Channel', 'Post', 'Template']