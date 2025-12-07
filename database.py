# telegram_poster/database.py
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import os


class Database:
    def __init__(self, db_path: str = 'telegram_poster.db'):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Создаем соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица ботов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_token TEXT UNIQUE NOT NULL,
                    bot_username TEXT,
                    bot_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица каналов/групп
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    title TEXT,
                    username TEXT,
                    type TEXT, -- channel, group, private
                    bot_id INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (bot_id) REFERENCES bots (id)
                )
            ''')

            # Таблица публикаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    status TEXT DEFAULT 'draft', -- draft, scheduled, sent, error
                    scheduled_time TIMESTAMP,
                    sent_time TIMESTAMP,
                    media_path TEXT,
                    buttons_json TEXT DEFAULT '[]',
                    repeat_interval TEXT, -- daily, weekly, monthly, none
                    repeat_count INTEGER DEFAULT 0,
                    repeat_until TIMESTAMP,
                    error_message TEXT,
                    bot_id INTEGER,
                    template_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица шаблонов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    buttons_json TEXT DEFAULT '[]',
                    media_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица медиа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_type TEXT, -- photo, video, document
                    file_size INTEGER,
                    post_id INTEGER,
                    template_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    # CRUD операции для ботов
    def add_bot(self, bot_token: str, bot_username: str = None, bot_name: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bots (bot_token, bot_username, bot_name)
                VALUES (?, ?, ?)
            ''', (bot_token, bot_username, bot_name))
            conn.commit()
            return cursor.lastrowid

    def get_bots(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bots WHERE is_active = 1')
            return [dict(row) for row in cursor.fetchall()]

    # CRUD операции для каналов
    def add_channel(self, chat_id: str, title: str, username: str = None,
                    type: str = 'channel', bot_id: int = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO channels (chat_id, title, username, type, bot_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, title, username, type, bot_id))
            conn.commit()
            return cursor.lastrowid

    def get_channels(self, bot_id: int = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if bot_id:
                cursor.execute('SELECT * FROM channels WHERE bot_id = ? AND is_active = 1', (bot_id,))
            else:
                cursor.execute('SELECT * FROM channels WHERE is_active = 1')
            return [dict(row) for row in cursor.fetchall()]

    # CRUD операции для публикаций
    def add_post(self, content: str, channel_id: str, status: str = 'draft',
                 scheduled_time: str = None, media_path: str = None,
                 buttons: List[Dict] = None, bot_id: int = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            buttons_json = json.dumps(buttons) if buttons else '[]'

            cursor.execute('''
                INSERT INTO posts (content, channel_id, status, scheduled_time, 
                                 media_path, buttons_json, bot_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (content, channel_id, status, scheduled_time, media_path, buttons_json, bot_id))
            conn.commit()
            return cursor.lastrowid

    def update_post_status(self, post_id: int, status: str, error_message: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 'sent':
                cursor.execute('''
                    UPDATE posts 
                    SET status = ?, sent_time = CURRENT_TIMESTAMP, error_message = NULL
                    WHERE id = ?
                ''', (status, post_id))
            elif status == 'error':
                cursor.execute('''
                    UPDATE posts 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                ''', (status, error_message, post_id))
            else:
                cursor.execute('''
                    UPDATE posts 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, post_id))
            conn.commit()

    def get_posts(self, status: str = None, bot_id: int = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute('''
                    SELECT * FROM posts 
                    WHERE status = ? AND bot_id = ?
                    ORDER BY scheduled_time ASC
                ''', (status, bot_id))
            else:
                cursor.execute('''
                    SELECT * FROM posts 
                    WHERE bot_id = ?
                    ORDER BY scheduled_time ASC
                ''', (bot_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_post(self, post_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
            conn.commit()

    # CRUD операции для шаблонов
    def add_template(self, name: str, content: str, buttons: List[Dict] = None,
                     media_path: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            buttons_json = json.dumps(buttons) if buttons else '[]'

            cursor.execute('''
                INSERT INTO templates (name, content, buttons_json, media_path)
                VALUES (?, ?, ?, ?)
            ''', (name, content, buttons_json, media_path))
            conn.commit()
            return cursor.lastrowid

    def get_templates(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM templates ORDER BY updated_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_template(self, template_id: int, name: str = None, content: str = None,
                        buttons: List[Dict] = None, media_path: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []

            if name:
                updates.append("name = ?")
                params.append(name)
            if content:
                updates.append("content = ?")
                params.append(content)
            if buttons:
                updates.append("buttons_json = ?")
                params.append(json.dumps(buttons))
            if media_path:
                updates.append("media_path = ?")
                params.append(media_path)

            updates.append("updated_at = CURRENT_TIMESTAMP")

            params.append(template_id)

            query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

    # Получение статистики
    def get_stats(self, bot_id: int) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END) as scheduled,
                       SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                       SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error
                FROM posts WHERE bot_id = ?
            ''', (bot_id,))

            stats = dict(cursor.fetchone())

            # Последние публикации
            cursor.execute('''
                SELECT * FROM posts 
                WHERE bot_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            ''', (bot_id,))

            recent_posts = [dict(row) for row in cursor.fetchall()]

            return {
                'stats': stats,
                'recent_posts': recent_posts
            }


# Создаем глобальный экземпляр БД
db = Database()