# telegram_poster/telegram_api.py
import requests
import os
import mimetypes
from typing import List, Dict, Optional, Union, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramAPI:
    """Класс для работы с Telegram Bot API"""

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, bot_token: str):
        """
        Инициализация API с токеном бота

        Args:
            bot_token: Токен бота, полученный от @BotFather
        """
        self.bot_token = bot_token
        self.api_url = f"{self.BASE_URL}{bot_token}"

    def _make_request(self, method: str, data: Optional[Dict] = None,
                      files: Optional[Dict] = None, timeout: int = 30) -> Optional[Dict]:
        """
        Выполнение HTTP-запроса к Telegram API

        Args:
            method: Метод API (например, 'getMe', 'sendMessage')
            data: Данные для отправки
            files: Файлы для загрузки
            timeout: Таймаут запроса

        Returns:
            Ответ API в виде словаря или None при ошибке
        """
        try:
            url = f"{self.api_url}/{method}"

            if files:
                response = requests.post(url, data=data, files=files, timeout=timeout)
            else:
                response = requests.post(url, json=data, timeout=timeout)

            response.raise_for_status()
            result = response.json()

            if not result.get('ok'):
                error_code = result.get('error_code', 'unknown')
                description = result.get('description', 'No error description')
                logger.error(f"Telegram API error {error_code}: {description}")
                return None

            return result.get('result')

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while calling Telegram API method: {method}")
            return None

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while calling Telegram API method: {method}")
            return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for method {method}")
            return None

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response for method {method}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error in method {method}: {str(e)}")
            return None

    def validate_token(self, token: Optional[str] = None) -> bool:
        """
        Проверка валидности токена бота через метод getMe

        Args:
            token: Токен для проверки (если None, используется self.bot_token)

        Returns:
            True если токен валиден, False в противном случае
        """
        check_token = token or self.bot_token

        # Сохраняем оригинальный токен
        original_token = self.bot_token
        original_api_url = self.api_url

        try:
            # Временно меняем токен для проверки
            self.bot_token = check_token
            self.api_url = f"{self.BASE_URL}{check_token}"

            result = self._make_request('getMe')

            if result:
                logger.info(f"Token is valid. Bot username: @{result.get('username')}")
                return True
            return False

        finally:
            # Возвращаем оригинальный токен
            self.bot_token = original_token
            self.api_url = original_api_url

    def send_message(self, chat_id: Union[str, int], text: str,
                     buttons: Optional[List[Dict]] = None,
                     media_path: Optional[str] = None,
                     parse_mode: str = "HTML",
                     disable_web_page_preview: bool = False,
                     disable_notification: bool = False) -> Optional[int]:
        """
        Отправка сообщения в чат/канал

        Args:
            chat_id: ID чата или канала
            text: Текст сообщения
            buttons: Список кнопок в формате Telegram InlineKeyboardMarkup
            media_path: Путь к медиафайлу (фото, видео, документ)
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
            disable_web_page_preview: Отключить превью ссылок
            disable_notification: Отключить уведомление

        Returns:
            ID отправленного сообщения или None при ошибке
        """
        try:
            # Если есть медиафайл, отправляем его с подписью
            if media_path and os.path.exists(media_path):
                message_id = self._send_media(chat_id, text, media_path, buttons,
                                              parse_mode, disable_notification)
                return message_id

            # Отправка текстового сообщения
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview,
                'disable_notification': disable_notification
            }

            # Добавляем кнопки если есть
            if buttons:
                keyboard = self._create_keyboard(buttons)
                if keyboard:
                    data['reply_markup'] = json.dumps(keyboard)

            result = self._make_request('sendMessage', data=data)

            if result:
                return result.get('message_id')
            return None

        except Exception as e:
            logger.error(f"Error sending message to chat {chat_id}: {str(e)}")
            return None

    def _send_media(self, chat_id: Union[str, int], text: str, media_path: str,
                    buttons: Optional[List[Dict]] = None, parse_mode: str = "HTML",
                    disable_notification: bool = False) -> Optional[int]:
        """
        Отправка медиафайла с подписью

        Args:
            chat_id: ID чата или канала
            text: Текст подписи
            media_path: Путь к медиафайлу
            buttons: Список кнопок
            parse_mode: Режим парсинга
            disable_notification: Отключить уведомление

        Returns:
            ID отправленного сообщения или None при ошибке
        """
        try:
            # Определяем тип медиафайла
            mime_type, _ = mimetypes.guess_type(media_path)

            if not mime_type:
                logger.error(f"Could not determine MIME type for file: {media_path}")
                # Пытаемся отправить как документ
                return self._send_document(chat_id, text, media_path, buttons,
                                           parse_mode, disable_notification)

            if mime_type.startswith('image/'):
                return self._send_photo(chat_id, text, media_path, buttons,
                                        parse_mode, disable_notification)
            elif mime_type.startswith('video/'):
                return self._send_video(chat_id, text, media_path, buttons,
                                        parse_mode, disable_notification)
            elif mime_type.startswith('audio/'):
                return self._send_audio(chat_id, text, media_path, buttons,
                                        parse_mode, disable_notification)
            else:
                return self._send_document(chat_id, text, media_path, buttons,
                                           parse_mode, disable_notification)

        except Exception as e:
            logger.error(f"Error sending media to chat {chat_id}: {str(e)}")
            return None

    def _send_photo(self, chat_id: Union[str, int], text: str, photo_path: str,
                    buttons: Optional[List[Dict]] = None, parse_mode: str = "HTML",
                    disable_notification: bool = False) -> Optional[int]:
        """Отправка фото"""
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': chat_id,
                    'caption': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification
                }

                if buttons:
                    keyboard = self._create_keyboard(buttons)
                    if keyboard:
                        data['reply_markup'] = json.dumps(keyboard)

                result = self._make_request('sendPhoto', data=data, files=files)
                return result.get('message_id') if result else None

        except FileNotFoundError:
            logger.error(f"Photo file not found: {photo_path}")
            return None
        except Exception as e:
            logger.error(f"Error sending photo: {str(e)}")
            return None

    def _send_video(self, chat_id: Union[str, int], text: str, video_path: str,
                    buttons: Optional[List[Dict]] = None, parse_mode: str = "HTML",
                    disable_notification: bool = False) -> Optional[int]:
        """Отправка видео"""
        try:
            with open(video_path, 'rb') as video:
                files = {'video': video}
                data = {
                    'chat_id': chat_id,
                    'caption': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification
                }

                if buttons:
                    keyboard = self._create_keyboard(buttons)
                    if keyboard:
                        data['reply_markup'] = json.dumps(keyboard)

                result = self._make_request('sendVideo', data=data, files=files)
                return result.get('message_id') if result else None

        except FileNotFoundError:
            logger.error(f"Video file not found: {video_path}")
            return None
        except Exception as e:
            logger.error(f"Error sending video: {str(e)}")
            return None

    def _send_document(self, chat_id: Union[str, int], text: str, document_path: str,
                       buttons: Optional[List[Dict]] = None, parse_mode: str = "HTML",
                       disable_notification: bool = False) -> Optional[int]:
        """Отправка документа"""
        try:
            with open(document_path, 'rb') as document:
                files = {'document': document}
                data = {
                    'chat_id': chat_id,
                    'caption': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification
                }

                if buttons:
                    keyboard = self._create_keyboard(buttons)
                    if keyboard:
                        data['reply_markup'] = json.dumps(keyboard)

                result = self._make_request('sendDocument', data=data, files=files)
                return result.get('message_id') if result else None

        except FileNotFoundError:
            logger.error(f"Document file not found: {document_path}")
            return None
        except Exception as e:
            logger.error(f"Error sending document: {str(e)}")
            return None

    def _send_audio(self, chat_id: Union[str, int], text: str, audio_path: str,
                    buttons: Optional[List[Dict]] = None, parse_mode: str = "HTML",
                    disable_notification: bool = False) -> Optional[int]:
        """Отправка аудио"""
        try:
            with open(audio_path, 'rb') as audio:
                files = {'audio': audio}
                data = {
                    'chat_id': chat_id,
                    'caption': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification
                }

                if buttons:
                    keyboard = self._create_keyboard(buttons)
                    if keyboard:
                        data['reply_markup'] = json.dumps(keyboard)

                result = self._make_request('sendAudio', data=data, files=files)
                return result.get('message_id') if result else None

        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            return None
        except Exception as e:
            logger.error(f"Error sending audio: {str(e)}")
            return None

    def _create_keyboard(self, buttons: List[Dict]) -> Optional[Dict]:
        """
        Создание клавиатуры из списка кнопок

        Args:
            buttons: Список кнопок в формате:
                    [{'text': 'Button1', 'url': 'https://...'}, ...]
                    или вложенный список для рядов:
                    [[{'text': 'Button1'}, {'text': 'Button2'}], ...]

        Returns:
            Словарь с клавиатурой в формате Telegram API
        """
        if not buttons:
            return None

        try:
            # Если это плоский список, делаем его вложенным
            if isinstance(buttons[0], dict):
                keyboard = [buttons]
            elif isinstance(buttons[0], list):
                keyboard = buttons
            else:
                logger.error("Invalid buttons format")
                return None

            return {'inline_keyboard': keyboard}

        except Exception as e:
            logger.error(f"Error creating keyboard: {str(e)}")
            return None

    def get_channels(self) -> List[Dict]:
        """
        Получение списка каналов/чатов, где есть бот

        Note: Telegram API не предоставляет прямого метода для получения списка чатов.
        Этот метод использует getUpdates для получения последних обновлений и извлечения
        информации о чатах из них.

        Returns:
            Список словарей с информацией о каналах/чатах
        """
        try:
            # Получаем последние обновления
            data = {
                'offset': -100,
                'limit': 100,
                'timeout': 1
            }

            result = self._make_request('getUpdates', data=data)
            if not result:
                return []

            channels = []
            seen_chats = set()

            for update in result:
                chat = None

                # Ищем информацию о чате в разных типах обновлений
                if 'message' in update:
                    chat = update['message'].get('chat')
                elif 'channel_post' in update:
                    chat = update['channel_post'].get('chat')
                elif 'edited_message' in update:
                    chat = update['edited_message'].get('chat')
                elif 'edited_channel_post' in update:
                    chat = update['edited_channel_post'].get('chat')
                elif 'callback_query' in update:
                    chat = update['callback_query'].get('message', {}).get('chat')

                if chat and chat.get('id') and chat['id'] not in seen_chats:
                    seen_chats.add(chat['id'])

                    channel_info = {
                        'chat_id': chat['id'],
                        'title': chat.get('title') or chat.get('first_name', '') +
                                 (' ' + chat.get('last_name', '') if chat.get('last_name') else ''),
                        'username': chat.get('username'),
                        'type': chat.get('type', 'unknown')
                    }

                    # Получаем дополнительную информацию о чате
                    chat_details = self.get_chat(chat['id'])
                    if chat_details:
                        channel_info.update({
                            'title': chat_details.get('title', channel_info['title']),
                            'username': chat_details.get('username', channel_info['username']),
                            'description': chat_details.get('description'),
                            'members_count': chat_details.get('members_count'),
                        })

                    channels.append(channel_info)

            return channels

        except Exception as e:
            logger.error(f"Error getting channels: {str(e)}")
            return []

    def get_chat(self, chat_id: Union[str, int]) -> Optional[Dict]:
        """
        Получение информации о чате/канале

        Args:
            chat_id: ID чата или канала

        Returns:
            Словарь с информацией о чате или None при ошибке
        """
        try:
            data = {'chat_id': chat_id}
            result = self._make_request('getChat', data=data)
            return result

        except Exception as e:
            logger.error(f"Error getting chat {chat_id}: {str(e)}")
            return None

    def edit_message(self, chat_id: Union[str, int], message_id: int,
                     text: str, parse_mode: str = "HTML",
                     buttons: Optional[List[Dict]] = None,
                     disable_web_page_preview: bool = False) -> bool:
        """
        Редактирование существующего сообщения

        Args:
            chat_id: ID чата или канала
            message_id: ID сообщения для редактирования
            text: Новый текст сообщения
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
            buttons: Новые кнопки (если None, кнопки не изменяются)
            disable_web_page_preview: Отключить превью ссылок

        Returns:
            True если сообщение успешно отредактировано, False в противном случае
        """
        try:
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }

            # Если переданы кнопки, обновляем клавиатуру
            if buttons is not None:
                if buttons:
                    keyboard = self._create_keyboard(buttons)
                    if keyboard:
                        data['reply_markup'] = json.dumps(keyboard)
                else:
                    # Удаляем клавиатуру
                    data['reply_markup'] = json.dumps({'inline_keyboard': []})

            result = self._make_request('editMessageText', data=data)

            if result:
                logger.info(f"Message {message_id} in chat {chat_id} edited successfully")
                return True

            logger.warning(f"Failed to edit message {message_id} in chat {chat_id}")
            return False

        except Exception as e:
            logger.error(f"Error editing message {message_id} in chat {chat_id}: {str(e)}")
            return False

    def delete_message(self, chat_id: Union[str, int], message_id: int) -> bool:
        """
        Удаление сообщения

        Args:
            chat_id: ID чата или канала
            message_id: ID сообщения для удаления

        Returns:
            True если сообщение успешно удалено, False в противном случае
        """
        try:
            data = {
                'chat_id': chat_id,
                'message_id': message_id
            }

            result = self._make_request('deleteMessage', data=data)
            return bool(result)

        except Exception as e:
            logger.error(f"Error deleting message {message_id} in chat {chat_id}: {str(e)}")
            return False

    def get_bot_info(self) -> Optional[Dict]:
        """
        Получение информации о боте

        Returns:
            Словарь с информацией о боте или None при ошибке
        """
        try:
            result = self._make_request('getMe')
            return result

        except Exception as e:
            logger.error(f"Error getting bot info: {str(e)}")
            return None

    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирование подключения и прав бота

        Returns:
            Словарь с результатами теста
        """
        result = {
            'token_valid': False,
            'bot_username': None,
            'can_send_messages': False,
            'error': None
        }

        try:
            # Проверяем токен
            bot_info = self.get_bot_info()
            if not bot_info:
                result['error'] = 'Invalid token or connection error'
                return result

            result['token_valid'] = True
            result['bot_username'] = bot_info.get('username')

            # Пытаемся отправить тестовое сообщение себе (боту)
            test_result = self.send_message(
                chat_id=bot_info['id'],
                text=f"Test message from {bot_info['username']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                disable_notification=True
            )

            result['can_send_messages'] = bool(test_result)

            if not test_result:
                result['error'] = 'Bot cannot send messages (might be blocked or restricted)'

            return result

        except Exception as e:
            result['error'] = str(e)
            return result


# Функции для удобства использования без создания экземпляра класса

def validate_token(token: str) -> bool:
    """
    Быстрая проверка токена

    Args:
        token: Токен бота

    Returns:
        True если токен валиден, False в противном случае
    """
    api = TelegramAPI(token)
    return api.validate_token()


def get_bot_info(token: str) -> Optional[Dict]:
    """
    Получение информации о боте по токену

    Args:
        token: Токен бота

    Returns:
        Словарь с информацией о боте или None при ошибке
    """
    api = TelegramAPI(token)
    return api.get_bot_info()


if __name__ == "__main__":
    # Пример использования
    import sys

    if len(sys.argv) > 1:
        token = sys.argv[1]
        api = TelegramAPI(token)

        # Тестируем подключение
        print("Testing Telegram bot connection...")
        test_result = api.test_connection()

        if test_result['token_valid']:
            print(f"✓ Token is valid")
            print(f"✓ Bot: @{test_result['bot_username']}")
            print(f"✓ Can send messages: {test_result['can_send_messages']}")

            # Получаем список каналов
            channels = api.get_channels()
            print(f"\nFound {len(channels)} channels/groups:")
            for channel in channels:
                print(f"  - {channel['title']} (ID: {channel['chat_id']}, Type: {channel['type']})")
        else:
            print(f"✗ Error: {test_result['error']}")
    else:
        print("Usage: python telegram_api.py <bot_token>")
        print("Example: python telegram_api.py 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")