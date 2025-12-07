# telegram_poster/utils/notifications.py
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Union
from enum import Enum

from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.metrics import dp

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Типы уведомлений"""
    SUCCESS = 'success'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    LOADING = 'loading'


class Notification:
    """Класс для управления уведомлениями"""

    # Цвета для разных типов уведомлений
    TYPE_COLORS = {
        NotificationType.SUCCESS: [0.2, 0.8, 0.4, 1],  # Зеленый
        NotificationType.ERROR: [0.9, 0.3, 0.3, 1],  # Красный
        NotificationType.WARNING: [1.0, 0.7, 0.2, 1],  # Оранжевый
        NotificationType.INFO: [0.2, 0.6, 0.9, 1],  # Синий
        NotificationType.LOADING: [0.5, 0.5, 0.5, 1],  # Серый
    }

    # Иконки для разных типов уведомлений
    TYPE_ICONS = {
        NotificationType.SUCCESS: '✓',
        NotificationType.ERROR: '✗',
        NotificationType.WARNING: '⚠',
        NotificationType.INFO: 'ℹ',
        NotificationType.LOADING: '⏳',
    }

    def __init__(self, app=None):
        """
        Инициализация менеджера уведомлений

        Args:
            app: Ссылка на основное приложение
        """
        self.app = app
        self.current_popup = None
        self.current_toast = None
        self.notification_queue = []
        self.is_showing = False

    def show_popup(self, title: str, message: str,
                   notification_type: NotificationType = NotificationType.INFO,
                   buttons: Optional[list] = None,
                   auto_close: bool = False,
                   close_timeout: int = 5) -> Popup:
        """
        Показать всплывающее окно с уведомлением

        Args:
            title: Заголовок уведомления
            message: Текст сообщения
            notification_type: Тип уведомления
            buttons: Список кнопок в формате [{'text': '...', 'action': callable}, ...]
            auto_close: Автоматически закрывать через timeout
            close_timeout: Время до автоматического закрытия (в секундах)

        Returns:
            Созданное всплывающее окно
        """
        try:
            # Закрываем предыдущее всплывающее окно если есть
            if self.current_popup:
                self.current_popup.dismiss()

            # Создаем контент всплывающего окна
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(20))

            # Заголовок
            title_label = Label(
                text=f"[b]{title}[/b]",
                markup=True,
                font_size=dp(18),
                size_hint_y=None,
                height=dp(30),
                color=[0.2, 0.2, 0.2, 1]
            )
            content.add_widget(title_label)

            # Иконка типа уведомления
            icon_label = Label(
                text=self.TYPE_ICONS.get(notification_type, 'ℹ'),
                font_size=dp(40),
                size_hint_y=None,
                height=dp(50),
                color=self.TYPE_COLORS.get(notification_type, [0.5, 0.5, 0.5, 1])
            )
            content.add_widget(icon_label)

            # Сообщение
            message_label = Label(
                text=message,
                font_size=dp(16),
                size_hint_y=None,
                height=dp(100),
                color=[0.4, 0.4, 0.4, 1],
                halign='center',
                valign='middle'
            )
            message_label.bind(texture_size=message_label.setter('size'))
            content.add_widget(message_label)

            # Кнопки
            if buttons is None:
                buttons = [{'text': 'OK', 'action': None}]

            buttons_layout = BoxLayout(
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10)
            )

            for btn_config in buttons:
                btn = Button(
                    text=btn_config['text'],
                    font_size=dp(16),
                    background_color=self.TYPE_COLORS.get(notification_type, [0.2, 0.6, 0.9, 1])
                )

                if btn_config.get('action'):
                    btn.bind(on_release=lambda instance, action=btn_config['action']: action())

                btn.bind(on_release=lambda instance: popup.dismiss())
                buttons_layout.add_widget(btn)

            content.add_widget(buttons_layout)

            # Создаем всплывающее окно
            popup = Popup(
                title='',
                content=content,
                size_hint=(0.8, 0.5),
                auto_dismiss=False,
                separator_color=[0, 0, 0, 0],
                background_color=[1, 1, 1, 1]
            )

            # Устанавливаем цвет фона в зависимости от типа уведомления
            popup.background = ''
            with popup.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(*self.TYPE_COLORS.get(notification_type, [0.2, 0.6, 0.9, 1]))
                RoundedRectangle(pos=popup.pos, size=popup.size, radius=[dp(15), ])

            self.current_popup = popup

            # Автоматическое закрытие если включено
            if auto_close:
                Clock.schedule_once(lambda dt: popup.dismiss(), close_timeout)

            popup.open()
            return popup

        except Exception as e:
            logger.error(f"Error showing popup notification: {str(e)}")
            return None

    def show_toast(self, message: str,
                   notification_type: NotificationType = NotificationType.INFO,
                   duration: int = 3) -> Optional[ModalView]:
        """
        Показать toast-уведомление (всплывающее снизу)

        Args:
            message: Текст сообщения
            notification_type: Тип уведомления
            duration: Длительность показа в секундах

        Returns:
            Созданное toast-уведомление
        """
        try:
            # Закрываем предыдущий toast если есть
            if self.current_toast:
                self.current_toast.dismiss()

            # Создаем контент toast
            content = BoxLayout(
                orientation='horizontal',
                spacing=dp(10),
                padding=[dp(15), dp(10)],
                size_hint=(None, None),
                size=(dp(300), dp(60))
            )

            # Устанавливаем цвет фона
            content.canvas.before.clear()
            with content.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(*self.TYPE_COLORS.get(notification_type, [0.2, 0.6, 0.9, 1]))
                RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10), ])

            # Иконка
            icon_label = Label(
                text=self.TYPE_ICONS.get(notification_type, 'ℹ'),
                font_size=dp(20),
                size_hint_x=None,
                width=dp(30),
                color=[1, 1, 1, 1]
            )
            content.add_widget(icon_label)

            # Сообщение
            message_label = Label(
                text=message,
                font_size=dp(14),
                color=[1, 1, 1, 1],
                halign='left',
                valign='middle'
            )
            content.add_widget(message_label)

            # Создаем ModalView для toast
            toast = ModalView(
                size_hint=(None, None),
                size=(dp(300), dp(60)),
                background_color=[0, 0, 0, 0],
                background='',
                overlay_color=[0, 0, 0, 0]
            )

            toast.add_widget(content)

            # Позиционируем toast снизу экрана
            toast.pos = (
                (Window.width - toast.width) / 2,
                -toast.height  # Начинаем ниже экрана
            )

            # Анимация появления
            anim = Animation(
                y=dp(50),  # Поднимаем на 50 пикселей от нижнего края
                duration=0.3,
                t='out_back'
            )

            # Анимация исчезновения
            def dismiss_animation():
                anim_out = Animation(
                    y=-toast.height,
                    duration=0.3,
                    t='in_back'
                )
                anim_out.start(toast)
                anim_out.bind(on_complete=lambda *args: toast.dismiss())

            # Запускаем анимации
            toast.open()
            anim.start(toast)

            # Запланировать закрытие
            Clock.schedule_once(lambda dt: dismiss_animation(), duration)

            self.current_toast = toast
            return toast

        except Exception as e:
            logger.error(f"Error showing toast notification: {str(e)}")
            return None

    def show_loading(self, message: str = "Загрузка...") -> Popup:
        """
        Показать окно загрузки

        Args:
            message: Сообщение загрузки

        Returns:
            Окно загрузки
        """
        try:
            content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(30))

            # Анимированная иконка загрузки
            from kivy.uix.spinner import Spinner
            spinner = Spinner(
                size_hint=(None, None),
                size=(dp(50), dp(50)),
                color=[0.2, 0.6, 0.9, 1],
                active=True
            )
            content.add_widget(spinner)

            # Сообщение
            message_label = Label(
                text=message,
                font_size=dp(16),
                color=[0.4, 0.4, 0.4, 1]
            )
            content.add_widget(message_label)

            popup = Popup(
                title='',
                content=content,
                size_hint=(0.6, 0.4),
                auto_dismiss=False,
                background_color=[1, 1, 1, 0.9]
            )

            popup.open()
            return popup

        except Exception as e:
            logger.error(f"Error showing loading notification: {str(e)}")
            return None

    def success(self, message: str, title: str = "Успешно", **kwargs):
        """Уведомление об успехе"""
        return self.show_popup(
            title=title,
            message=message,
            notification_type=NotificationType.SUCCESS,
            **kwargs
        )

    def error(self, message: str, title: str = "Ошибка", **kwargs):
        """Уведомление об ошибке"""
        return self.show_popup(
            title=title,
            message=message,
            notification_type=NotificationType.ERROR,
            **kwargs
        )

    def warning(self, message: str, title: str = "Внимание", **kwargs):
        """Предупреждающее уведомление"""
        return self.show_popup(
            title=title,
            message=message,
            notification_type=NotificationType.WARNING,
            **kwargs
        )

    def info(self, message: str, title: str = "Информация", **kwargs):
        """Информационное уведомление"""
        return self.show_popup(
            title=title,
            message=message,
            notification_type=NotificationType.INFO,
            **kwargs
        )

    def toast_success(self, message: str, duration: int = 3):
        """Toast об успехе"""
        return self.show_toast(
            message=message,
            notification_type=NotificationType.SUCCESS,
            duration=duration
        )

    def toast_error(self, message: str, duration: int = 3):
        """Toast об ошибке"""
        return self.show_toast(
            message=message,
            notification_type=NotificationType.ERROR,
            duration=duration
        )

    def send_notification(self, success: bool,
                          post_id: Optional[int] = None,
                          channel_name: Optional[str] = None,
                          error_message: Optional[str] = None,
                          use_toast: bool = True):
        """
        Уведомление об отправке публикации

        Args:
            success: Успешна ли отправка
            post_id: ID публикации (опционально)
            channel_name: Название канала (опционально)
            error_message: Сообщение об ошибке (если есть)
            use_toast: Использовать ли toast вместо popup
        """
        if success:
            message = "Публикация отправлена успешно!"
            if channel_name:
                message = f"Публикация в '{channel_name}' отправлена успешно!"

            if post_id:
                message += f" (ID: {post_id})"

            if use_toast:
                self.toast_success(message)
            else:
                self.success(message)
        else:
            message = "Ошибка отправки публикации"
            if channel_name:
                message = f"Ошибка отправки в '{channel_name}'"

            if error_message:
                message += f": {error_message}"

            if post_id:
                message += f" (ID: {post_id})"

            if use_toast:
                self.toast_error(message)
            else:
                self.error(message)

    def queue_notification(self, notification_type: NotificationType,
                           message: str, title: str = None, **kwargs):
        """
        Поставить уведомление в очередь

        Args:
            notification_type: Тип уведомления
            message: Текст сообщения
            title: Заголовок (если None, используется по умолчанию для типа)
            **kwargs: Дополнительные параметры
        """
        if title is None:
            title = {
                NotificationType.SUCCESS: "Успешно",
                NotificationType.ERROR: "Ошибка",
                NotificationType.WARNING: "Внимание",
                NotificationType.INFO: "Информация",
                NotificationType.LOADING: "Загрузка"
            }.get(notification_type, "Уведомление")

        self.notification_queue.append({
            'type': notification_type,
            'title': title,
            'message': message,
            'kwargs': kwargs
        })

        if not self.is_showing:
            self._show_next_notification()

    def _show_next_notification(self):
        """Показать следующее уведомление из очереди"""
        if not self.notification_queue:
            self.is_showing = False
            return

        self.is_showing = True
        notification = self.notification_queue.pop(0)

        if notification['type'] == NotificationType.LOADING:
            self.show_loading(notification['message'])
        else:
            self.show_popup(
                title=notification['title'],
                message=notification['message'],
                notification_type=notification['type'],
                **notification['kwargs']
            )

        # Запланировать показ следующего уведомления через 500 мс
        Clock.schedule_once(lambda dt: self._show_next_notification(), 0.5)


class NotificationWidget(BoxLayout):
    """Виджет для отображения уведомлений внутри экрана"""

    message = StringProperty('')
    notification_type = StringProperty('info')
    duration = NumericProperty(3)
    is_visible = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = 0
        self.opacity = 0
        self._anim = None

    def show(self, message: str, notification_type: str = 'info', duration: int = 3):
        """
        Показать уведомление

        Args:
            message: Текст сообщения
            notification_type: Тип уведомления
            duration: Длительность показа
        """
        if self._anim:
            self._anim.cancel(self)

        self.message = message
        self.notification_type = notification_type
        self.duration = duration

        # Анимация появления
        self._anim = Animation(height=dp(50), opacity=1, duration=0.3)
        self._anim.start(self)
        self.is_visible = True

        # Автоматическое скрытие
        Clock.schedule_once(lambda dt: self.hide(), duration)

    def hide(self):
        """Скрыть уведомление"""
        if self._anim:
            self._anim.cancel(self)

        self._anim = Animation(height=0, opacity=0, duration=0.3)
        self._anim.start(self)
        self.is_visible = False


# Создаем глобальный экземпляр менеджера уведомлений
notifications = NotificationManager()


class NotificationManager:
    """Глобальный менеджер уведомлений для приложения"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.notifier = Notification()
        return cls._instance

    def __getattr__(self, name):
        return getattr(self.notifier, name)


# Короткие алиасы для удобства
def notify_success(message: str, **kwargs):
    """Быстрое уведомление об успехе"""
    notifications.success(message, **kwargs)


def notify_error(message: str, **kwargs):
    """Быстрое уведомление об ошибке"""
    notifications.error(message, **kwargs)


def notify_warning(message: str, **kwargs):
    """Быстрое предупреждение"""
    notifications.warning(message, **kwargs)


def notify_info(message: str, **kwargs):
    """Быстрое информационное уведомление"""
    notifications.info(message, **kwargs)


def toast_success(message: str, duration: int = 3):
    """Быстрый toast об успехе"""
    notifications.toast_success(message, duration)


def toast_error(message: str, duration: int = 3):
    """Быстрый toast об ошибке"""
    notifications.toast_error(message, duration)