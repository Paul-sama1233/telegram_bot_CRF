# telegram_poster/main.py
import os

os.environ['KIVY_NO_ARGS'] = '1'

from kivy.config import Config

Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')
Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
import sys

# Добавляем пути к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем наши модули
from database import db
from telegram_api import TelegramAPI
from scheduler import Scheduler

# Импортируем экраны
from screens.posts_screen import PostsScreen, PostCard
from screens.create_post_screen import CreatePostScreen
from screens.templates_screen import TemplatesScreen, TemplateCard

# Загружаем KV файлы
kv_files = [
    'ui/auth_screen.kv',
    'ui/main_menu_screen.kv',
    'ui/posts_screen.kv',
    'ui/create_post_screen.kv',
    'ui/templates_screen.kv'
]

for kv_file in kv_files:
    kv_path = os.path.join(os.path.dirname(__file__), kv_file)
    if os.path.exists(kv_path):
        Builder.load_file(kv_path)
    else:
        print(f"Warning: KV file not found: {kv_path}")


# Определяем экраны (уже импортированы выше)
class AuthScreen(Screen):
    """Экран авторизации"""
    pass


class MainMenuScreen(Screen):
    """Главное меню"""
    pass


class SettingsScreen(Screen):
    """Настройки"""
    pass


class TelegramPosterApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sm = ScreenManager()
        self.telegram_api = None
        self.scheduler = None
        self.current_bot = None
        self.db = db

    def build(self):
        self.title = "Telegram Poster"
        Window.clearcolor = get_color_from_hex('#f5f5f5')

        # Создаем экраны
        self.sm.add_widget(AuthScreen(name='auth'))
        self.sm.add_widget(MainMenuScreen(name='main_menu'))
        self.sm.add_widget(PostsScreen(name='posts'))
        self.sm.add_widget(CreatePostScreen(name='create_post'))
        self.sm.add_widget(TemplatesScreen(name='templates'))
        self.sm.add_widget(SettingsScreen(name='settings'))

        # Сохраняем ссылку на app в ScreenManager
        self.sm.app = self

        # Проверяем, есть ли сохраненный бот
        bots = db.get_bots()
        if bots:
            # Переходим в главное меню
            self.current_bot = bots[0]
            self.telegram_api = TelegramAPI(self.current_bot['bot_token'])
            self.scheduler = Scheduler(self.telegram_api, db)
            self.sm.current = 'main_menu'
        else:
            # Показываем экран авторизации
            self.sm.current = 'auth'

        return self.sm

    def on_stop(self):
        """Очистка при выходе"""
        if self.scheduler:
            self.scheduler.stop()
        return super().on_stop()


if __name__ == '__main__':
    TelegramPosterApp().run()