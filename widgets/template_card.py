# telegram_poster/widgets/template_card.py

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.behaviors import ButtonBehavior
import json


class TemplateCard(BoxLayout):
    """Карточка шаблона с названием, текстом, кнопками"""

    # Свойства
    template_id = NumericProperty(0)
    template_name = StringProperty('')
    template_content = StringProperty('')
    has_media = StringProperty('')
    media_type = StringProperty('')
    button_count = NumericProperty(0)
    created_at = StringProperty('')

    # События
    on_use = None
    on_edit = None
    on_delete = None
    on_copy = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None

    def on_kv_post(self, base_widget):
        """Инициализация после загрузки KV"""
        parent = self.parent
        while parent and not hasattr(parent, 'app'):
            parent = parent.parent
        if parent and hasattr(parent, 'app'):
            self.app = parent.app

    def use_template(self):
        """Использовать шаблон"""
        if self.on_use:
            self.on_use(self.template_id)
        elif self.app:
            # Переходим на экран создания поста с этим шаблоном
            if hasattr(self.app, 'root') and hasattr(self.app.root, 'current_screen'):
                create_screen = self.app.root.get_screen('create_post')
                if hasattr(create_screen, 'load_template'):
                    create_screen.load_template(self.template_id)
                    self.app.root.current = 'create_post'

    def edit_template(self):
        """Редактировать шаблон"""
        if self.on_edit:
            self.on_edit(self.template_id)
        elif self.app:
            # Показываем диалог редактирования
            self.show_edit_dialog()

    def delete_template(self):
        """Удалить шаблон"""
        if self.on_delete:
            self.on_delete(self.template_id)
        elif self.app:
            self.show_delete_dialog()

    def copy_template(self):
        """Создать копию шаблона"""
        if self.on_copy:
            self.on_copy(self.template_id)
        elif self.app:
            # Логика копирования
            print(f"Копировать шаблон {self.template_id}")

    def get_short_content(self, max_length=100):
        """Сокращенный текст для отображения"""
        if len(self.template_content) <= max_length:
            return self.template_content
        return self.template_content[:max_length] + "..."

    def show_delete_dialog(self):
        """Показать диалог подтверждения удаления"""
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label

        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(
            text=f'Удалить шаблон "{self.template_name}"?',
            font_size='16sp'
        ))

        buttons = BoxLayout(spacing=10, size_hint_y=None, height=50)

        def confirm_delete(instance):
            if self.app and hasattr(self.app, 'db'):
                # В реальном приложении нужно добавить метод удаления шаблона
                # Пока просто удаляем из списка
                pass
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
            title='Удаление шаблона',
            content=content,
            size_hint=(0.8, 0.4)
        )
        popup.open()

    def show_edit_dialog(self):
        """Показать диалог редактирования"""
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput

        content = BoxLayout(orientation='vertical', spacing=10, padding=20)

        name_input = TextInput(
            text=self.template_name,
            hint_text='Название шаблона',
            multiline=False
        )

        content_input = TextInput(
            text=self.template_content,
            hint_text='Текст шаблона',
            multiline=True,
            size_hint_y=None,
            height=200
        )

        content.add_widget(Label(text='Название:', font_size='14sp'))
        content.add_widget(name_input)
        content.add_widget(Label(text='Текст:', font_size='14sp'))
        content.add_widget(content_input)

        buttons = BoxLayout(spacing=10, size_hint_y=None, height=50)

        def save_template(instance):
            # Сохраняем изменения
            if self.app and hasattr(self.app, 'db'):
                # В реальном приложении обновляем в БД
                self.template_name = name_input.text
                self.template_content = content_input.text
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        save_btn = Button(text='Сохранить', background_color=(0.26, 0.65, 0.96, 1))
        save_btn.bind(on_release=save_template)

        cancel_btn = Button(text='Отмена', background_color=(0.8, 0.8, 0.8, 1))
        cancel_btn.bind(on_release=cancel)

        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(
            title='Редактирование шаблона',
            content=content,
            size_hint=(0.9, 0.9)
        )
        popup.open()

    def show_media_preview(self):
        """Показать превью медиа"""
        if not self.has_media:
            return

        # Та же логика, что и в PostCard
        pass