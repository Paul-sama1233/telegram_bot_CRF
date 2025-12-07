# telegram_poster/screens/create_post_screen.py
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from datetime import datetime, timedelta
import json
import os

class CreatePostScreen(Screen):
    """Экран создания публикации"""
    post_content = StringProperty()
    selected_channel = StringProperty('')
    selected_template = StringProperty('')
    media_path = StringProperty('')
    schedule_date = StringProperty('')
    schedule_time = StringProperty('')
    repeat_interval = StringProperty('none')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self.channels = []
        self.templates = []
    
    def on_enter(self):
        """При входе на экран"""
        self.app = self.manager.app
        self.load_channels()
        self.load_templates()
        
        # Устанавливаем дату и время по умолчанию
        tomorrow = datetime.now() + timedelta(days=1)
        self.schedule_date = tomorrow.strftime('%Y-%m-%d')
        self.schedule_time = '12:00'
    
    def load_channels(self):
        """Загрузка каналов"""
        if not self.app or not self.app.db:
            return
        
        self.channels = self.app.db.get_channels(bot_id=self.app.current_bot['id'])
        
        # Обновляем Spinner
        if hasattr(self, 'channel_spinner'):
            self.channel_spinner.values = [c['title'] for c in self.channels]
            if self.channels:
                self.channel_spinner.text = self.channels[0]['title']
                self.selected_channel = self.channels[0]['chat_id']
    
    def load_templates(self):
        """Загрузка шаблонов"""
        if not self.app or not self.app.db:
            return
        
        self.templates = self.app.db.get_templates()
        
        # Обновляем Spinner
        if hasattr(self, 'template_spinner'):
            template_names = ['Без шаблона'] + [t['name'] for t in self.templates]
            self.template_spinner.values = template_names
            self.template_spinner.text = 'Без шаблона'
            self.selected_template = ''
    
    def on_channel_selected(self, spinner, text):
        """Выбор канала"""
        for channel in self.channels:
            if channel['title'] == text:
                self.selected_channel = channel['chat_id']
                break
    
    def on_template_selected(self, spinner, text):
        """Выбор шаблона"""
        if text == 'Без шаблона':
            self.selected_template = ''
            self.post_content = ''
        else:
            for template in self.templates:
                if template['name'] == text:
                    self.selected_template = str(template['id'])
                    self.post_content = template['content']
                    break
    
    def add_media(self):
        """Добавить медиафайл"""
        # Здесь будет логика выбора файла
        print("Добавить медиа")
    
    def add_button(self):
        """Добавить кнопку"""
        # Здесь будет логика добавления кнопки
        print("Добавить кнопку")
    
    def save_as_draft(self):
        """Сохранить как черновик"""
        self.save_post('draft')
    
    def schedule_post(self):
        """Запланировать публикацию"""
        self.save_post('scheduled')
    
    def send_now(self):
        """Отправить сейчас"""
        self.save_post('sent')
    
    def save_post(self, status):
        """Сохранение публикации"""
        if not self.app or not self.app.db:
            return
        
        if not self.post_content:
            self.show_error("Введите текст публикации")
            return
        
        if not self.selected_channel:
            self.show_error("Выберите канал")
            return
        
        try:
            # Формируем время публикации
            scheduled_time = None
            if status in ['scheduled', 'sent']:
                try:
                    dt_str = f"{self.schedule_date} {self.schedule_time}"
                    scheduled_time = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                except:
                    scheduled_time = datetime.now() + timedelta(minutes=5)
            
            # Сохраняем в БД
            post_id = self.app.db.add_post(
                content=self.post_content,
                channel_id=self.selected_channel,
                status=status,
                scheduled_time=scheduled_time.isoformat() if scheduled_time else None,
                media_path=self.media_path if self.media_path else None,
                buttons=[],  # Здесь можно добавить кнопки
                bot_id=self.app.current_bot['id']
            )
            
            if post_id:
                # Очищаем форму
                self.post_content = ''
                self.media_path = ''
                
                # Показываем сообщение об успехе
                self.show_success("Публикация сохранена")
                
                # Возвращаемся к списку
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'posts'), 1)
        
        except Exception as e:
            self.show_error(f"Ошибка сохранения: {str(e)}")
    
    def show_error(self, message):
        """Показать ошибку"""
        popup = Popup(
            title='Ошибка',
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        )
        popup.open()
    
    def show_success(self, message):
        """Показать сообщение об успехе"""
        popup = Popup(
            title='Успешно',
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        )
        popup.open()
