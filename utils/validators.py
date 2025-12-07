# telegram_poster/utils/validators.py
import re
import urllib.parse
from datetime import datetime, date, time
from typing import Optional, Tuple, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


class Validators:
    """Класс для валидации различных данных"""

    # Регулярные выражения для валидации
    URL_REGEX = re.compile(
        r'^(?:http|ftp)s?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # домен
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # или ip
        r'(?::\d+)?'  # порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    TELEGRAM_URL_REGEX = re.compile(
        r'^(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/)?([a-zA-Z0-9_]+)/?$'
    )

    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    PHONE_REGEX = re.compile(
        r'^\+?[1-9]\d{1,14}$'  # E.164 формат
    )

    def __init__(self):
        # Максимальные длины для Telegram
        self.max_lengths = {
            'text': 4096,  # Максимальная длина текста сообщения
            'caption': 1024,  # Максимальная длина подписи к медиа
            'button_text': 64,  # Максимальная длина текста кнопки
            'button_url': 2000,  # Максимальная длина URL кнопки
            'callback_data': 64,  # Максимальная длина callback данных
            'inline_query': 256,  # Максимальная длина inline query
            'hashtag': 256,  # Максимальная длина хэштега
            'username': 32,  # Максимальная длина username
        }

        # Запрещенные символы/слова
        self.forbidden_patterns = [
            r'<script.*?>.*?</script>',  # JavaScript
            r'on\w+\s*=',  # Обработчики событий
            r'javascript:',  # JavaScript URL
            r'data:',  # Data URL
        ]

    def validate_url(self, url: str,
                     allowed_schemes: Tuple[str, ...] = ('http', 'https'),
                     require_telegram: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Валидация URL

        Args:
            url: URL для проверки
            allowed_schemes: Разрешенные схемы
            require_telegram: Требовать ли Telegram URL

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        if not url or not isinstance(url, str):
            return False, "URL должен быть строкой"

        url = url.strip()

        # Проверка максимальной длины
        if len(url) > self.max_lengths['button_url']:
            return False, f"URL слишком длинный (макс. {self.max_lengths['button_url']} символов)"

        # Проверка Telegram URL если требуется
        if require_telegram:
            if self.TELEGRAM_URL_REGEX.match(url):
                return True, None
            else:
                return False, "Некорректный Telegram URL. Формат: t.me/username или telegram.me/username"

        # Общая проверка URL
        try:
            result = urllib.parse.urlparse(url)

            # Проверка схемы
            if result.scheme and result.scheme not in allowed_schemes:
                return False, f"Недопустимая схема URL. Разрешены: {', '.join(allowed_schemes)}"

            # Если схема не указана, добавляем https://
            if not result.scheme:
                url = f'https://{url}'
                result = urllib.parse.urlparse(url)

            # Проверка netloc (домена)
            if not result.netloc:
                return False, "URL должен содержать доменное имя"

            # Проверка по регулярному выражению
            if not self.URL_REGEX.match(url):
                return False, "Некорректный формат URL"

            # Проверка на запрещенные схемы
            forbidden_schemes = ['javascript', 'data', 'file']
            if any(url.lower().startswith(f"{scheme}:") for scheme in forbidden_schemes):
                return False, "Запрещенная схема URL"

            return True, None

        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False, f"Ошибка проверки URL: {str(e)}"

    def validate_text(self, text: str,
                      field_name: str = 'text',
                      max_length: Optional[int] = None,
                      min_length: int = 0,
                      allow_empty: bool = False,
                      check_xss: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Валидация текста

        Args:
            text: Текст для проверки
            field_name: Название поля (для сообщения об ошибке)
            max_length: Максимальная длина (если None, используется значение по умолчанию)
            min_length: Минимальная длина
            allow_empty: Разрешать ли пустой текст
            check_xss: Проверять ли на XSS уязвимости

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        if text is None:
            text = ''

        if not isinstance(text, str):
            return False, f"{field_name} должен быть строкой"

        text = text.strip()

        # Проверка на пустоту
        if not text and not allow_empty:
            return False, f"{field_name} не может быть пустым"

        # Определяем максимальную длину
        if max_length is None:
            max_length = self.max_lengths.get(field_name, 4096)

        # Проверка длины
        if len(text) > max_length:
            return False, f"{field_name} слишком длинный (макс. {max_length} символов, сейчас {len(text)})"

        if len(text) < min_length and not (allow_empty and not text):
            return False, f"{field_name} слишком короткий (мин. {min_length} символов, сейчас {len(text)})"

        # Проверка на XSS уязвимости
        if check_xss:
            for pattern in self.forbidden_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False, f"{field_name} содержит потенциально опасный код"

        # Проверка на недопустимые символы (опционально)
        # Например, можно добавить проверку на управляющие символы

        return True, None

    def validate_datetime(self, date_str: str,
                          time_str: str,
                          timezone_offset: int = 0) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Валидация даты и времени

        Args:
            date_str: Дата в формате YYYY-MM-DD
            time_str: Время в формате HH:MM
            timezone_offset: Смещение часового пояса в часах

        Returns:
            Кортеж (валиден, сообщение_об_ошибке, объект datetime)
        """
        try:
            # Парсим дату
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return False, "Некорректный формат даты. Используйте YYYY-MM-DD", None

            # Парсим время
            try:
                time_obj = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                return False, "Некорректный формат времени. Используйте HH:MM", None

            # Создаем полный datetime объект
            datetime_obj = datetime.combine(date_obj, time_obj)

            # Применяем смещение часового пояса
            if timezone_offset:
                from datetime import timedelta
                datetime_obj += timedelta(hours=timezone_offset)

            # Проверяем, что время в будущем
            current_time = datetime.now()
            if datetime_obj <= current_time:
                return False, "Время публикации должно быть в будущем", None

            # Проверяем, что не слишком далеко в будущем (например, не более 1 года)
            max_future = current_time.replace(year=current_time.year + 1)
            if datetime_obj > max_future:
                return False, "Время публикации не может быть более чем через год", None

            return True, None, datetime_obj

        except Exception as e:
            logger.error(f"Error validating datetime {date_str} {time_str}: {str(e)}")
            return False, f"Ошибка проверки времени: {str(e)}", None

    def validate_time_string(self, time_str: str,
                             format: str = '%H:%M') -> Tuple[bool, Optional[str]]:
        """
        Валидация строки времени

        Args:
            time_str: Строка времени
            format: Ожидаемый формат

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        try:
            time_obj = datetime.strptime(time_str, format).time()
            return True, None
        except ValueError:
            return False, f"Некорректный формат времени. Используйте {format}"
        except Exception as e:
            logger.error(f"Error validating time string {time_str}: {str(e)}")
            return False, f"Ошибка проверки времени: {str(e)}"

    def validate_date_string(self, date_str: str,
                             format: str = '%Y-%m-%d') -> Tuple[bool, Optional[str]]:
        """
        Валидация строки даты

        Args:
            date_str: Строка даты
            format: Ожидаемый формат

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        try:
            date_obj = datetime.strptime(date_str, format).date()

            # Проверяем, что дата не в прошлом (опционально)
            current_date = date.today()
            if date_obj < current_date:
                return False, "Дата не может быть в прошлом"

            return True, None
        except ValueError:
            return False, f"Некорректный формат даты. Используйте {format}"
        except Exception as e:
            logger.error(f"Error validating date string {date_str}: {str(e)}")
            return False, f"Ошибка проверки даты: {str(e)}"

    def validate_telegram_entity(self, entity: str,
                                 entity_type: str = 'username') -> Tuple[bool, Optional[str]]:
        """
        Валидация Telegram сущностей (username, chat_id и т.д.)

        Args:
            entity: Сущность для проверки
            entity_type: Тип сущности ('username', 'chat_id', 'hashtag')

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        if not entity or not isinstance(entity, str):
            return False, f"{entity_type} должен быть строкой"

        entity = entity.strip()

        if entity_type == 'username':
            # Telegram username: 5-32 символов, начинается с буквы, содержит только буквы, цифры и underscores
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', entity):
                return False, "Некорректный Telegram username. Должен начинаться с буквы, содержать только буквы, цифры и underscores, длиной 5-32 символа"

            if len(entity) > self.max_lengths['username']:
                return False, f"Username слишком длинный (макс. {self.max_lengths['username']} символов)"

        elif entity_type == 'chat_id':
            # Chat ID может быть числом или строкой с минусом для каналов/групп
            if not (entity.lstrip('-').isdigit() or
                    (entity.startswith('@') and re.match(r'^@[a-zA-Z0-9_]{5,32}$', entity))):
                return False, "Некорректный Chat ID. Должен быть числом или username начиная с @"

        elif entity_type == 'hashtag':
            # Hashtag: начинается с #, содержит буквы, цифры, underscores
            if not re.match(r'^#[a-zA-Z0-9_]+$', entity):
                return False, "Некорректный хэштег. Должен начинаться с # и содержать только буквы, цифры и underscores"

            if len(entity) > self.max_lengths['hashtag']:
                return False, f"Хэштег слишком длинный (макс. {self.max_lengths['hashtag']} символов)"

        return True, None

    def validate_bot_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация токена Telegram бота

        Args:
            token: Токен бота

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        if not token or not isinstance(token, str):
            return False, "Токен должен быть строкой"

        token = token.strip()

        # Проверка формата токена: цифры:буквы_и_цифры
        if not re.match(r'^\d+:[a-zA-Z0-9_-]+$', token):
            return False, "Некорректный формат токена. Должен быть в формате 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

        # Проверка длины
        if len(token) < 20:
            return False, "Токен слишком короткий"
        if len(token) > 100:
            return False, "Токен слишком длинный"

        return True, None

    def validate_buttons(self, buttons: list,
                         max_buttons: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Валидация инлайн-кнопок

        Args:
            buttons: Список кнопок
            max_buttons: Максимальное количество кнопок

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        if not isinstance(buttons, list):
            return False, "Кнопки должны быть списком"

        if len(buttons) > max_buttons:
            return False, f"Слишком много кнопок (макс. {max_buttons})"

        for i, button in enumerate(buttons):
            if not isinstance(button, dict):
                return False, f"Кнопка {i + 1} должна быть словарем"

            # Проверяем обязательные поля
            if 'text' not in button:
                return False, f"Кнопка {i + 1} не содержит текст"

            # Валидируем текст кнопки
            is_valid, error = self.validate_text(
                button['text'],
                field_name='button_text',
                max_length=self.max_lengths['button_text'],
                allow_empty=False
            )

            if not is_valid:
                return False, f"Кнопка {i + 1}: {error}"

            # Проверяем наличие URL или callback_data
            has_url = 'url' in button
            has_callback = 'callback_data' in button

            if not (has_url or has_callback):
                return False, f"Кнопка {i + 1} должна содержать либо url, либо callback_data"

            if has_url and has_callback:
                return False, f"Кнопка {i + 1} не может содержать одновременно url и callback_data"

            # Валидируем URL если есть
            if has_url:
                is_valid, error = self.validate_url(button['url'])
                if not is_valid:
                    return False, f"Кнопка {i + 1}: {error}"

            # Валидируем callback_data если есть
            if has_callback:
                callback_data = str(button['callback_data'])
                if len(callback_data) > self.max_lengths['callback_data']:
                    return False, f"Кнопка {i + 1}: callback_data слишком длинный (макс. {self.max_lengths['callback_data']} символов)"

        return True, None

    def validate_repeat_interval(self, interval: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация интервала повторения

        Args:
            interval: Интервал повторения

        Returns:
            Кортеж (валиден, сообщение_об_ошибке)
        """
        valid_intervals = ['none', 'daily', 'weekly', 'monthly', 'custom']

        if interval not in valid_intervals:
            return False, f"Некорректный интервал повторения. Допустимые значения: {', '.join(valid_intervals)}"

        return True, None

    def validate_media_file(self, file_path: str,
                            allowed_types: Tuple[str, ...] = ('photo', 'video', 'document', 'audio'),
                            max_size_mb: int = 50) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Валидация медиафайла

        Args:
            file_path: Путь к файлу
            allowed_types: Разрешенные типы файлов
            max_size_mb: Максимальный размер в мегабайтах

        Returns:
            Кортеж (валиден, сообщение_об_ошибке, информация_о_файле)
        """
        try:
            import os
            from .file_handlers import file_handler

            # Проверяем существование файла
            if not os.path.exists(file_path):
                return False, "Файл не найден", None

            # Получаем информацию о файле
            file_info = file_handler.get_file_info(file_path)
            if 'error' in file_info:
                return False, file_info['error'], None

            # Проверяем размер файла
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_info['size'] > max_size_bytes:
                size_mb = file_info['size'] / (1024 * 1024)
                return False, f"Файл слишком большой ({size_mb:.1f} MB). Максимальный размер: {max_size_mb} MB", None

            # Проверяем тип файла
            if file_info['type'] not in allowed_types:
                return False, f"Тип файла не поддерживается. Разрешены: {', '.join(allowed_types)}", None

            # Дополнительные проверки для конкретных типов
            if file_info['type'] == 'photo':
                # Можно добавить проверку размеров изображения
                pass
            elif file_info['type'] == 'video':
                # Можно добавить проверку длительности видео
                pass

            return True, None, file_info

        except Exception as e:
            logger.error(f"Error validating media file {file_path}: {str(e)}")
            return False, f"Ошибка проверки файла: {str(e)}", None


# Создаем глобальный экземпляр валидатора
validators = Validators()