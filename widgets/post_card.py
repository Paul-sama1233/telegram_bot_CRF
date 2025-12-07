# telegram_poster/widgets/post_card.py

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.clock import Clock

import json
from datetime import datetime


class AvatarButton(ButtonBehavior, Image):
    """Кнопка-аватар"""
    pass


class StatusIndicator(BoxLayout):
    """Индикатор статуса"""
    status = StringProperty('draft')

    def on_status(self, instance, value):
        """Обновление цвета при изменении статуса"""
        colors = {
            'draft': (1, 0.65, 0.1, 1),  # оранжевый
            'scheduled': (0.26, 0.65, 0.96, 1),  # синий
            'sent': (0.4, 0.73, 0.42, 1),  # зеленый
            'error': (0.94, 0.33, 0.31, 1)  # красный
        }
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*colors.get(value, (0.46, 0.46, 0.46, 1)))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10, ])


class TimeLabel(Label):
    """Метка времени с иконкой"""
    pass


class PostCard(BoxLayout):
    """Карточка публикации с аватаром, текстом, статусом, временем"""

    # Свойства
    post_id = NumericProperty(0)
    avatar_source = StringProperty('')
    username = StringProperty('')
    post_text = StringProperty('')
    status = StringProperty('draft')
    time_text = StringProperty('')
    channel_name = StringProperty('')
    has_media = StringProperty('')  # путь к медиа или пустая строка
    media_type = StringProperty('')  # photo, video, document, audio

    # События
    on_edit = None
    on_delete = None
    on_send = None
    on_copy = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None

        # Устанавливаем стандартный аватар
        if not self.avatar_source:
            self.avatar_source = 'assets/icons/default_avatar.png'

    def on_kv_post(self, base_widget):
        """Инициализация после загрузки KV"""
        # Ищем ссылку на app через иерархию виджетов
        parent = self.parent
        while parent and not hasattr(parent, 'app'):
            parent = parent.parent
        if parent and hasattr(parent, 'app'):
            self.app = parent.app

    def get_status_color(self):
        """Получить цвет статуса"""
        colors = {
            'draft': (1, 0.65, 0.1, 1),  # оранжевый
            'scheduled': (0.26, 0.65, 0.96, 1),  # синий
            'sent': (0.4, 0.73, 0.42, 1),  # зеленый
            'error': (0.94, 0.33, 0.31, 1)  # красный
        }
        return colors.get(self.status, (0.46, 0.46, 0.46, 1))

    def get_status_text(self):
        """Получить текстовое представление статуса"""
        texts = {
            'draft': 'Черновик',
            'scheduled': 'Запланировано',
            'sent': 'Отправлено',
            'error': 'Ошибка'
        }
        return texts.get(self.status, self.status)

    def edit_post(self):
        """Редактировать публикацию"""
        if self.on_edit:
            self.on_edit(self.post_id)
        elif self.app:
            # Переходим на экран редактирования
            from kivy.app import App
            app = App.get_running_app()
            if hasattr(app.root, 'current_screen') and hasattr(app.root.current_screen, 'edit_post'):
                app.root.current_screen.edit_post(self.post_id)

    def delete_post(self):
        """Удалить публикацию"""
        if self.on_delete:
            self.on_delete(self.post_id)
        elif self.app:
            # Показываем диалог подтверждения
            self.show_delete_dialog()

    def send_post(self):
        """Отправить публикацию"""
        if self.on_send:
            self.on_send(self.post_id)
        elif self.app:
            # Логика отправки
            print(f"Отправить пост {self.post_id}")

    def copy_post(self):
        """Копировать публикацию"""
        if self.on_copy:
            self.on_copy(self.post_id)
        elif self.app:
            # Логика копирования
            print(f"Копировать пост {self.post_id}")

    def show_delete_dialog(self):
        """Показать диалог подтверждения удаления"""
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label

        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(
            text='Вы уверены, что хотите удалить эту публикацию?',
            font_size='16sp'
        ))

        buttons = BoxLayout(spacing=10, size_hint_y=None, height=50)

        def confirm_delete(instance):
            if self.app and hasattr(self.app, 'db'):
                self.app.db.delete_post(self.post_id)
                # Обновляем список постов
                if self.parent and hasattr(self.parent, 'load_posts'):
                    self.parent.load_posts()
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        confirm_btn = Button(text='Удалить', background_color=(0.94, 0.33, 0.31, 1))
        confirm_btn.bind(on_release=confirm_delete)

        cancel_btn = Button(text='Отмена', background_color=(0.8, 0.8, 0.8, 1))
        cancel_btn.bind(on_release=cancel)

        buttons.add_widget(confirm_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(
            title='Удаление публикации',
            content=content,
            size_hint=(0.8, 0.4)
        )
        popup.open()

    def show_media_preview(self):
        """Показать превью медиа"""
        if not self.has_media:
            return

        from kivy.uix.popup import Popup
        from kivy.uix.image import Image
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout

        content = BoxLayout(orientation='vertical')

        if self.media_type == 'photo':
            img = Image(source=self.has_media)
            content.add_widget(img)
        else:
            icon = '📁' if self.media_type == 'document' else '🎵' if self.media_type == 'audio' else '🎬'
            content.add_widget(Label(
                text=f"{icon} {self.media_type}",
                font_size='24sp'
            ))
            content.add_widget(Label(
                text=f"Файл: {self.has_media.split('/')[-1]}",
                font_size='14sp'
            ))

        popup = Popup(
            title='Превью медиа',
            content=content,
            size_hint=(0.9, 0.9)
        )
        popup.open()