# telegram_poster/screens/templates_screen.py
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
import json

class TemplateCard(BoxLayout):
    """Карточка шаблона"""
    template_id = StringProperty()
    template_name = StringProperty()
    template_content = StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
    
    def on_kv_post(self, base_widget):
        """Инициализация после загрузки KV"""
        self.app = self.parent.parent.parent.parent.parent.app
    
    def use_template(self):
        """Использовать шаблон"""
        if self.app:
            print(f"Использовать шаблон {self.template_id}")
            # Переходим к созданию поста с этим шаблоном
            create_screen = self.app.root.get_screen('create_post')
            create_screen.post_content = self.template_content
            self.app.root.current = 'create_post'
    
    def edit_template(self):
        """Редактировать шаблон"""
        if self.app:
            print(f"Редактировать шаблон {self.template_id}")
            # Здесь будет логика редактирования шаблона
    
    def delete_template(self):
        """Удалить шаблон"""
        if self.app:
            print(f"Удалить шаблон {self.template_id}")
            # Здесь будет логика удаления шаблона

class TemplatesScreen(Screen):
    """Экран шаблонов"""
    templates_list = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
    
    def on_enter(self):
        """При входе на экран"""
        self.app = self.manager.app
        self.load_templates()
    
    def load_templates(self):
        """Загрузка шаблонов"""
        if not self.app or not self.app.db:
            return
        
        try:
            # Очищаем список
            if self.templates_list:
                self.templates_list.clear_widgets()
            
            # Загружаем шаблоны из БД
            templates_data = self.app.db.get_templates()
            
            # Создаем карточки
            for template_data in templates_data:
                template_card = TemplateCard()
                template_card.template_id = str(template_data['id'])
                template_card.template_name = template_data.get('name', 'Без названия')
                template_card.template_content = template_data.get('content', '')[:100] + '...' if len(template_data.get('content', '')) > 100 else template_data.get('content', '')
                
                self.templates_list.add_widget(template_card)
            
        except Exception as e:
            print(f"Ошибка загрузки шаблонов: {e}")
    
    def create_new_template(self):
        """Создать новый шаблон"""
        # Создаем всплывающее окно для ввода названия
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        name_input = TextInput(hint_text='Название шаблона', multiline=False)
        content.add_widget(name_input)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        
        def create_template(instance):
            if name_input.text.strip():
                # Создаем шаблон
                create_screen = self.app.root.get_screen('create_post')
                if create_screen.post_content:
                    self.app.db.add_template(
                        name=name_input.text.strip(),
                        content=create_screen.post_content,
                        buttons=[],
                        media_path=create_screen.media_path if create_screen.media_path else None
                    )
                    self.load_templates()
                    popup.dismiss()
                else:
                    self.show_error("Сначала создайте публикацию для шаблона")
        
        create_btn = Button(text='Создать', on_release=create_template)
        cancel_btn = Button(text='Отмена', on_release=lambda x: popup.dismiss())
        
        buttons_layout.add_widget(create_btn)
        buttons_layout.add_widget(cancel_btn)
        
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title='Создать шаблон',
            content=content,
            size_hint=(0.8, 0.4)
        )
        popup.open()
    
    def show_error(self, message):
        """Показать ошибку"""
        popup = Popup(
            title='Ошибка',
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        )
        popup.open()
