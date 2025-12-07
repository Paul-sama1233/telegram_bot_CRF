# telegram_poster/screens/posts_screen.py
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
import json

class PostCard(BoxLayout):
    """Карточка публикации"""
    post_id = StringProperty()
    title = StringProperty()
    content = StringProperty()
    status = StringProperty()
    channel_name = StringProperty()
    scheduled_time = StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
    
    def on_kv_post(self, base_widget):
        """Инициализация после загрузки KV"""
        self.app = self.parent.parent.parent.parent.parent.app
    
    def edit_post(self):
        """Редактировать публикацию"""
        if self.app:
            print(f"Редактировать пост {self.post_id}")
            # Здесь будет логика редактирования
    
    def delete_post(self):
        """Удалить публикацию"""
        if self.app:
            print(f"Удалить пост {self.post_id}")
            # Здесь будет логика удаления
    
    def send_now(self):
        """Отправить сейчас"""
        if self.app:
            print(f"Отправить сейчас пост {self.post_id}")
            # Здесь будет логика отправки

class PostsScreen(Screen):
    """Экран списка публикаций"""
    filter_status = StringProperty('all')
    posts_list = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self.posts = []
    
    def on_enter(self):
        """При входе на экран"""
        self.app = self.manager.app
        self.load_posts()
    
    def load_posts(self):
        """Загрузка публикаций"""
        if not self.app or not self.app.db:
            return
        
        try:
            # Очищаем список
            if self.posts_list:
                self.posts_list.clear_widgets()
            
            # Загружаем посты из БД
            posts_data = self.app.db.get_posts(bot_id=self.app.current_bot['id'])
            
            # Фильтрация по статусу
            if self.filter_status != 'all':
                posts_data = [p for p in posts_data if p['status'] == self.filter_status]
            
            # Сортируем по времени (новые сверху)
            posts_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Создаем карточки
            for post_data in posts_data:
                post_card = PostCard()
                post_card.post_id = str(post_data['id'])
                post_card.title = post_data.get('title', 'Без названия')
                post_card.content = post_data.get('content', '')[:100] + '...' if len(post_data.get('content', '')) > 100 else post_data.get('content', '')
                
                # Статус
                status = post_data.get('status', 'draft')
                post_card.status = status
                
                # Название канала
                channels = self.app.db.get_channels(bot_id=self.app.current_bot['id'])
                channel_name = 'Неизвестный канал'
                for channel in channels:
                    if str(channel['chat_id']) == str(post_data.get('channel_id')):
                        channel_name = channel.get('title', 'Канал')
                        break
                post_card.channel_name = channel_name
                
                # Время
                if post_data.get('scheduled_time'):
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(post_data['scheduled_time'])
                        post_card.scheduled_time = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        post_card.scheduled_time = post_data.get('scheduled_time', '')
                else:
                    post_card.scheduled_time = 'Не запланировано'
                
                self.posts_list.add_widget(post_card)
            
        except Exception as e:
            print(f"Ошибка загрузки постов: {e}")
    
    def set_filter(self, status):
        """Установить фильтр"""
        self.filter_status = status
        self.load_posts()
    
    def create_new_post(self):
        """Создать новую публикацию"""
        self.manager.current = 'create_post'
