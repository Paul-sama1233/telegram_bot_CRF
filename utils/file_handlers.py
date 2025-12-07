# telegram_poster/utils/file_handlers.py
import os
import shutil
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging

from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image
from PIL import Image as PILImage
import tempfile

logger = logging.getLogger(__name__)


class FileHandler:
    """Обработчик файлов для загрузки, сохранения и создания превью медиа"""

    # Расширения для разных типов медиа
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac'}
    DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.zip', '.rar'}

    def __init__(self, media_dir: str = 'media'):
        """
        Инициализация обработчика файлов

        Args:
            media_dir: Директория для хранения медиафайлов
        """
        self.media_dir = media_dir
        self.create_media_dirs()

    def create_media_dirs(self):
        """Создание директорий для медиафайлов"""
        dirs = [
            self.media_dir,
            os.path.join(self.media_dir, 'photos'),
            os.path.join(self.media_dir, 'videos'),
            os.path.join(self.media_dir, 'audio'),
            os.path.join(self.media_dir, 'documents'),
            os.path.join(self.media_dir, 'thumbnails')
        ]

        for directory in dirs:
            os.makedirs(directory, exist_ok=True)

    def get_file_type(self, file_path: str) -> str:
        """
        Определение типа файла по расширению

        Args:
            file_path: Путь к файлу

        Returns:
            Тип файла: 'photo', 'video', 'audio', 'document' или 'unknown'
        """
        ext = Path(file_path).suffix.lower()

        if ext in self.IMAGE_EXTENSIONS:
            return 'photo'
        elif ext in self.VIDEO_EXTENSIONS:
            return 'video'
        elif ext in self.AUDIO_EXTENSIONS:
            return 'audio'
        elif ext in self.DOCUMENT_EXTENSIONS:
            return 'document'
        else:
            return 'unknown'

    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Генерация уникального имени файла

        Args:
            original_filename: Оригинальное имя файла

        Returns:
            Уникальное имя файла с временной меткой и хэшем
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]
        name, ext = os.path.splitext(original_filename)

        return f"{timestamp}_{file_hash}{ext}"

    def save_media_file(self, source_path: str,
                        media_type: Optional[str] = None,
                        subfolder: Optional[str] = None) -> Dict[str, Any]:
        """
        Сохранение медиафайла в директорию приложения

        Args:
            source_path: Путь к исходному файлу
            media_type: Тип медиа (если None, определяется автоматически)
            subfolder: Подпапка для сохранения

        Returns:
            Словарь с информацией о сохраненном файле
        """
        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Файл не найден: {source_path}")

            # Определяем тип файла если не указан
            if media_type is None:
                media_type = self.get_file_type(source_path)

            # Создаем подпапку если указана
            save_dir = self.media_dir
            if subfolder:
                save_dir = os.path.join(save_dir, subfolder)
                os.makedirs(save_dir, exist_ok=True)
            elif media_type == 'photo':
                save_dir = os.path.join(self.media_dir, 'photos')
            elif media_type == 'video':
                save_dir = os.path.join(self.media_dir, 'videos')
            elif media_type == 'audio':
                save_dir = os.path.join(self.media_dir, 'audio')
            elif media_type == 'document':
                save_dir = os.path.join(self.media_dir, 'documents')

            # Генерируем уникальное имя
            original_name = os.path.basename(source_path)
            unique_name = self.generate_unique_filename(original_name)
            destination_path = os.path.join(save_dir, unique_name)

            # Копируем файл
            shutil.copy2(source_path, destination_path)

            # Получаем информацию о файле
            file_size = os.path.getsize(destination_path)

            # Создаем превью если это изображение
            thumbnail_path = None
            if media_type == 'photo':
                thumbnail_path = self.create_image_thumbnail(destination_path)

            return {
                'success': True,
                'original_path': source_path,
                'saved_path': destination_path,
                'original_name': original_name,
                'saved_name': unique_name,
                'media_type': media_type,
                'file_size': file_size,
                'thumbnail_path': thumbnail_path,
                'created_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error saving media file {source_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original_path': source_path
            }

    def create_image_thumbnail(self, image_path: str,
                               max_size: Tuple[int, int] = (200, 200),
                               quality: int = 85) -> Optional[str]:
        """
        Создание миниатюры для изображения

        Args:
            image_path: Путь к исходному изображению
            max_size: Максимальный размер превью (ширина, высота)
            quality: Качество JPEG (1-100)

        Returns:
            Путь к созданной миниатюре или None при ошибке
        """
        try:
            # Проверяем, что файл существует
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return None

            # Открываем изображение с помощью PIL
            with PILImage.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Вычисляем размеры для сохранения пропорций
                img.thumbnail(max_size, PILImage.Resampling.LANCZOS)

                # Сохраняем миниатюру
                thumb_dir = os.path.join(self.media_dir, 'thumbnails')
                os.makedirs(thumb_dir, exist_ok=True)

                thumb_name = f"thumb_{os.path.basename(image_path)}"
                thumb_path = os.path.join(thumb_dir, thumb_name)

                # Сохраняем в формате JPEG
                img.save(thumb_path, 'JPEG', quality=quality, optimize=True)

                return thumb_path

        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_path}: {str(e)}")
            return None

    def create_video_thumbnail(self, video_path: str,
                               frame_time: float = 5.0,
                               max_size: Tuple[int, int] = (200, 200)) -> Optional[str]:
        """
        Создание превью для видео (извлечение кадра)

        Args:
            video_path: Путь к видеофайлу
            frame_time: Время кадра для извлечения (в секундах)
            max_size: Максимальный размер превью

        Returns:
            Путь к созданному превью или None при ошибке
        """
        try:
            # Проверяем наличие библиотеки для работы с видео
            try:
                import cv2
            except ImportError:
                logger.warning("OpenCV not installed, video thumbnails disabled")
                return None

            # Проверяем, что файл существует
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None

            # Открываем видео
            cap = cv2.VideoCapture(video_path)

            # Получаем FPS и общее количество кадров
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Вычисляем номер кадра для извлечения
            frame_number = min(int(fps * frame_time), total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            # Читаем кадр
            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error(f"Failed to read frame from video: {video_path}")
                return None

            # Конвертируем BGR в RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Создаем изображение из кадра
            img = PILImage.fromarray(frame_rgb)

            # Изменяем размер
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)

            # Сохраняем миниатюру
            thumb_dir = os.path.join(self.media_dir, 'thumbnails')
            os.makedirs(thumb_dir, exist_ok=True)

            thumb_name = f"thumb_{os.path.basename(video_path).rsplit('.', 1)[0]}.jpg"
            thumb_path = os.path.join(thumb_dir, thumb_name)

            img.save(thumb_path, 'JPEG', quality=85, optimize=True)

            return thumb_path

        except Exception as e:
            logger.error(f"Error creating video thumbnail for {video_path}: {str(e)}")
            return None

    def get_media_preview(self, media_path: str,
                          media_type: Optional[str] = None,
                          preview_size: Tuple[int, int] = (200, 200)) -> Optional[Image]:
        """
        Создание виджета Image для превью медиафайла

        Args:
            media_path: Путь к медиафайлу
            media_type: Тип медиа (если None, определяется автоматически)
            preview_size: Размер превью

        Returns:
            Виджет Image для отображения превью или None при ошибке
        """
        try:
            if not os.path.exists(media_path):
                logger.error(f"Media file not found: {media_path}")
                return None

            if media_type is None:
                media_type = self.get_file_type(media_path)

            # Создаем превью если его еще нет
            thumbnail_path = None

            if media_type == 'photo':
                thumbnail_path = self.create_image_thumbnail(media_path, preview_size)
            elif media_type == 'video':
                thumbnail_path = self.create_video_thumbnail(media_path)

            # Если превью создано, возвращаем Image виджет
            if thumbnail_path and os.path.exists(thumbnail_path):
                return Image(source=thumbnail_path, size_hint=(None, None),
                             size=preview_size, keep_ratio=True)

            # Если не удалось создать превью, возвращаем иконку по типу файла
            icon_name = {
                'photo': 'image.png',
                'video': 'video.png',
                'audio': 'audio.png',
                'document': 'document.png',
                'unknown': 'file.png'
            }.get(media_type, 'file.png')

            # Попробуем найти иконку в assets
            icon_path = os.path.join('assets', 'icons', icon_name)
            if os.path.exists(icon_path):
                return Image(source=icon_path, size_hint=(None, None),
                             size=(preview_size[0] // 2, preview_size[1] // 2))

            # Если иконки нет, создаем текстовое представление
            from kivy.uix.label import Label
            return Label(text=f"[{media_type.upper()}]",
                         font_size='20sp', size=preview_size)

        except Exception as e:
            logger.error(f"Error creating media preview for {media_path}: {str(e)}")
            return None

    def delete_media_file(self, file_path: str,
                          delete_thumbnails: bool = True) -> bool:
        """
        Удаление медиафайла

        Args:
            file_path: Путь к файлу
            delete_thumbnails: Удалять ли связанные превью

        Returns:
            True если файл удален, False в противном случае
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found for deletion: {file_path}")
                return False

            # Удаляем основной файл
            os.remove(file_path)

            # Удаляем превью если нужно
            if delete_thumbnails:
                thumb_dir = os.path.join(self.media_dir, 'thumbnails')
                thumb_pattern = f"thumb_{os.path.basename(file_path)}"
                thumb_pattern_no_ext = f"thumb_{os.path.basename(file_path).rsplit('.', 1)[0]}"

                # Ищем и удаляем все связанные превью
                for thumb_file in os.listdir(thumb_dir):
                    if thumb_file.startswith(thumb_pattern) or thumb_file.startswith(thumb_pattern_no_ext):
                        thumb_path = os.path.join(thumb_dir, thumb_file)
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)

            return True

        except Exception as e:
            logger.error(f"Error deleting media file {file_path}: {str(e)}")
            return False

    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, int]:
        """
        Очистка старых файлов

        Args:
            days_old: Удалять файлы старше N дней

        Returns:
            Словарь с количеством удаленных файлов по типам
        """
        result = {'total': 0, 'photos': 0, 'videos': 0,
                  'audio': 0, 'documents': 0, 'thumbnails': 0}

        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)

            # Обходим все поддиректории
            for root, dirs, files in os.walk(self.media_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Получаем время модификации файла
                    mod_time = os.path.getmtime(file_path)

                    if mod_time < cutoff_time:
                        # Определяем тип файла по директории
                        rel_path = os.path.relpath(root, self.media_dir)

                        if rel_path == 'photos':
                            result['photos'] += 1
                        elif rel_path == 'videos':
                            result['videos'] += 1
                        elif rel_path == 'audio':
                            result['audio'] += 1
                        elif rel_path == 'documents':
                            result['documents'] += 1
                        elif rel_path == 'thumbnails':
                            result['thumbnails'] += 1

                        # Удаляем файл
                        os.remove(file_path)
                        result['total'] += 1

            return result

        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
            return result

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Получение информации о файле

        Args:
            file_path: Путь к файлу

        Returns:
            Словарь с информацией о файле
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            stat = os.stat(file_path)
            file_type = self.get_file_type(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'type': file_type,
                'mime_type': mime_type or 'application/octet-stream',
                'size': stat.st_size,
                'size_human': self._format_size(stat.st_size),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'extension': os.path.splitext(file_path)[1],
                'directory': os.path.dirname(file_path)
            }

        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {'error': str(e), 'path': file_path}

    def _format_size(self, size_bytes: int) -> str:
        """Форматирование размера файла в читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# Создаем глобальный экземпляр обработчика файлов
file_handler = FileHandler()