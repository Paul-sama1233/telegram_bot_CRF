# telegram_poster/widgets/button_editor.py

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, NumericProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock

import json


class ButtonEditor(BoxLayout):
    """Редактор инлайн-кнопок"""

    # Свойства
    buttons = ListProperty([])  # Список кнопок в формате [{"text": "...", "url": "..."}, ...]
    buttons_json = StringProperty('[]')  # JSON представление кнопок
    max_buttons = NumericProperty(10)  # Максимальное количество кнопок
    max_text_length = NumericProperty(64)  # Максимальная длина текста кнопки
    max_url_length = NumericProperty(2000)  # Максимальная длина URL

    # События
    on_buttons_changed = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_scheduled = False

    def on_buttons(self, instance, value):
        """При изменении списка кнопок"""
        self.buttons_json = json.dumps(value, ensure_ascii=False)
        self.update_buttons_display()

        # Вызываем callback если есть
        if self.on_buttons_changed:
            self.on_buttons_changed(value)

    def on_buttons_json(self, instance, value):
        """При изменении JSON кнопок"""
        try:
            new_buttons = json.loads(value) if value else []
            if new_buttons != self.buttons:
                self.buttons = new_buttons
        except:
            pass

    def update_buttons_display(self):
        """Обновить отображение кнопок"""
        if not hasattr(self, 'buttons_container'):
            return

        # Очищаем контейнер
        self.buttons_container.clear_widgets()

        if not self.buttons:
            # Показываем сообщение, если кнопок нет
            empty_label = Label(
                text='Нет кнопок. Нажмите "Добавить кнопку" для создания.',
                color=(0.5, 0.5, 0.5, 1),
                font_size='14sp',
                size_hint_y=None,
                height=40
            )
            self.buttons_container.add_widget(empty_label)
            return

        # Отображаем кнопки
        for i, btn in enumerate(self.buttons):
            btn_widget = ButtonItem(
                index=i,
                text=btn.get('text', ''),
                url=btn.get('url', ''),
                on_edit=self.edit_button,
                on_delete=self.delete_button,
                on_move_up=self.move_button_up,
                on_move_down=self.move_button_down
            )
            self.buttons_container.add_widget(btn_widget)

        # Обновляем статистику
        self.update_stats()

    def update_stats(self):
        """Обновить статистику"""
        if hasattr(self, 'stats_label'):
            stats_text = f"Кнопок: {len(self.buttons)}/{self.max_buttons}"
            self.stats_label.text = stats_text

    def add_button(self):
        """Добавить новую кнопку"""
        if len(self.buttons) >= self.max_buttons:
            self.show_message(f"Максимум {self.max_buttons} кнопок")
            return

        self.show_button_dialog()

    def edit_button(self, index):
        """Редактировать кнопку по индексу"""
        if 0 <= index < len(self.buttons):
            self.show_button_dialog(index)

    def delete_button(self, index):
        """Удалить кнопку по индексу"""
        if 0 <= index < len(self.buttons):
            self.show_confirm_dialog(
                "Удалить кнопку?",
                lambda: self._delete_button(index)
            )

    def _delete_button(self, index):
        """Удалить кнопку (без подтверждения)"""
        if 0 <= index < len(self.buttons):
            self.buttons.pop(index)
            self.update_buttons_display()

    def move_button_up(self, index):
        """Переместить кнопку вверх"""
        if index > 0:
            self.buttons[index], self.buttons[index - 1] = self.buttons[index - 1], self.buttons[index]
            self.update_buttons_display()

    def move_button_down(self, index):
        """Переместить кнопку вниз"""
        if index < len(self.buttons) - 1:
            self.buttons[index], self.buttons[index + 1] = self.buttons[index + 1], self.buttons[index]
            self.update_buttons_display()

    def show_button_dialog(self, index=None):
        """Показать диалог добавления/редактирования кнопки"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)

        # Текст кнопки
        text_label = Label(text='Текст кнопки:', size_hint_y=None, height=30)
        text_input = TextInput(
            hint_text='Например: Купить сейчас',
            multiline=False,
            size_hint_y=None,
            height=40
        )

        # URL
        url_label = Label(text='URL или callback:', size_hint_y=None, height=30)
        url_input = TextInput(
            hint_text='https://example.com или callback_data',
            multiline=False,
            size_hint_y=None,
            height=40
        )

        # Тип кнопки
        type_label = Label(text='Тип кнопки:', size_hint_y=None, height=30)
        type_spinner = Spinner(
            text='URL',
            values=['URL', 'Callback', 'Switch Inline Query', 'Login'],
            size_hint_y=None,
            height=40
        )

        # Заполняем значения если редактируем
        if index is not None and 0 <= index < len(self.buttons):
            btn = self.buttons[index]
            text_input.text = btn.get('text', '')
            url_input.text = btn.get('url', '')

        content.add_widget(text_label)
        content.add_widget(text_input)
        content.add_widget(url_label)
        content.add_widget(url_input)
        content.add_widget(type_label)
        content.add_widget(type_spinner)

        # Кнопки
        buttons = BoxLayout(spacing=10, size_hint_y=None, height=50)

        def save_button(instance):
            text = text_input.text.strip()
            url = url_input.text.strip()
            btn_type = type_spinner.text

            if not text:
                self.show_message("Введите текст кнопки")
                return

            if not url:
                self.show_message("Введите URL или callback данные")
                return

            # Валидация URL для типа URL
            if btn_type == 'URL' and not (url.startswith('http://') or url.startswith('https://')):
                self.show_message("URL должен начинаться с http:// или https://")
                return

            # Ограничение длины
            if len(text) > self.max_text_length:
                self.show_message(f"Текст кнопки не более {self.max_text_length} символов")
                return

            if len(url) > self.max_url_length:
                self.show_message(f"URL не более {self.max_url_length} символов")
                return

            # Создаем или обновляем кнопку
            button_data = {
                'text': text,
                'url': url,
                'type': btn_type.lower()
            }

            if index is None:
                # Добавляем новую кнопку
                self.buttons.append(button_data)
            else:
                # Обновляем существующую
                self.buttons[index] = button_data

            self.update_buttons_display()
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        save_text = 'Сохранить' if index is not None else 'Добавить'
        save_btn = Button(text=save_text, background_color=(0.26, 0.65, 0.96, 1))
        save_btn.bind(on_release=save_button)

        cancel_btn = Button(text='Отмена', background_color=(0.8, 0.8, 0.8, 1))
        cancel_btn.bind(on_release=cancel)

        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        title = 'Редактировать кнопку' if index is not None else 'Добавить кнопку'
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.9, 0.7)
        )
        popup.open()

    def show_confirm_dialog(self, message, callback):
        """Показать диалог подтверждения"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(text=message, font_size='16sp'))

        buttons = BoxLayout(spacing=10, size_hint_y=None, height=50)

        def confirm(instance):
            callback()
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        confirm_btn = Button(text='Да', background_color=(0.94, 0.33, 0.31, 1))
        confirm_btn.bind(on_release=confirm)

        cancel_btn = Button(text='Нет', background_color=(0.8, 0.8, 0.8, 1))
        cancel_btn.bind(on_release=cancel)

        buttons.add_widget(confirm_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(
            title='Подтверждение',
            content=content,
            size_hint=(0.8, 0.4)
        )
        popup.open()

    def show_message(self, message):
        """Показать сообщение"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(text=message, font_size='16sp'))

        buttons = BoxLayout(size_hint_y=None, height=50)

        def ok(instance):
            popup.dismiss()

        ok_btn = Button(text='OK')
        ok_btn.bind(on_release=ok)
        buttons.add_widget(ok_btn)
        content.add_widget(buttons)

        popup = Popup(
            title='Сообщение',
            content=content,
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def clear_buttons(self):
        """Очистить все кнопки"""
        if self.buttons:
            self.show_confirm_dialog(
                "Очистить все кнопки?",
                self._clear_buttons
            )

    def _clear_buttons(self):
        """Очистить все кнопки (без подтверждения)"""
        self.buttons = []
        self.update_buttons_display()

    def get_telegram_keyboard(self):
        """Получить клавиатуру в формате Telegram"""
        if not self.buttons:
            return None

        # Группируем кнопки в ряды (по 2 в ряд для лучшего вида)
        keyboard = []
        row = []

        for i, btn in enumerate(self.buttons):
            button_dict = {}

            if btn.get('type') == 'url':
                button_dict = {
                    'text': btn['text'],
                    'url': btn['url']
                }
            else:
                # Для callback кнопок
                button_dict = {
                    'text': btn['text'],
                    'callback_data': btn['url']
                }

            row.append(button_dict)

            # Создаем новый ряд после каждой 2-й кнопки
            if len(row) >= 2 or i == len(self.buttons) - 1:
                keyboard.append(row)
                row = []

        return keyboard


class ButtonItem(BoxLayout):
    """Элемент кнопки в редакторе"""

    index = NumericProperty(0)
    text = StringProperty('')
    url = StringProperty('')

    on_edit = ObjectProperty(None)
    on_delete = ObjectProperty(None)
    on_move_up = ObjectProperty(None)
    on_move_down = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.update_display)

    def update_display(self, dt=0):
        """Обновить отображение"""
        if hasattr(self, 'text_label'):
            self.text_label.text = self.text

        if hasattr(self, 'url_label'):
            # Сокращаем длинный URL
            if len(self.url) > 30:
                self.url_label.text = self.url[:27] + '...'
            else:
                self.url_label.text = self.url

    def edit(self):
        """Редактировать кнопку"""
        if self.on_edit:
            self.on_edit(self.index)

    def delete(self):
        """Удалить кнопку"""
        if self.on_delete:
            self.on_delete(self.index)

    def move_up(self):
        """Переместить вверх"""
        if self.on_move_up:
            self.on_move_up(self.index)

    def move_down(self):
        """Переместить вниз"""
        if self.on_move_down:
            self.on_move_down(self.index)