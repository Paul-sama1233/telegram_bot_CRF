# telegram_poster/scheduler.py
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from database import db
from telegram_api import TelegramAPI
from models.post import Post

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик отложенных публикаций"""

    def __init__(self, telegram_api: TelegramAPI, database=None):
        """
        Инициализация планировщика

        Args:
            telegram_api: Экземпляр TelegramAPI для отправки сообщений
            database: Экземпляр базы данных (опционально)
        """
        self.telegram_api = telegram_api
        self.db = database or db
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.is_running = False
        self.background_thread = None

    def start(self):
        """Запуск планировщика и фонового потока"""
        if not self.is_running:
            logger.info("Starting scheduler...")
            self.scheduler.start()
            self.is_running = True

            # Запускаем фоновый поток для проверки отложенных постов
            self.background_thread = threading.Thread(
                target=self._check_scheduled_posts_loop,
                daemon=True
            )
            self.background_thread.start()

            # Перепланируем повторяющиеся публикации при запуске
            self.reschedule_repeating_posts()
            logger.info("Scheduler started successfully")

    def stop(self):
        """Остановка планировщика"""
        if self.is_running:
            logger.info("Stopping scheduler...")
            self.is_running = False
            if self.background_thread:
                self.background_thread.join(timeout=5)
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def schedule_post(self, post: Post) -> bool:
        """
        Планирование публикации поста

        Args:
            post: Модель поста для планирования

        Returns:
            True если пост успешно запланирован, False в противном случае
        """
        try:
            # Проверяем, что время публикации в будущем
            if post.scheduled_time and post.scheduled_time <= datetime.now():
                logger.warning(f"Post {post.id} scheduled time is in the past")
                return False

            # Создаем уникальный идентификатор задачи
            job_id = f"post_{post.id}"

            # Удаляем существующую задачу, если есть
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Определяем триггер в зависимости от типа публикации
            if post.repeat_interval:
                # Повторяющаяся публикация
                trigger = self._create_repeating_trigger(post)
                job_args = {
                    'post_id': post.id,
                    'is_repeating': True,
                    'original_scheduled_time': post.scheduled_time
                }
            else:
                # Разовая публикация
                trigger = DateTrigger(run_date=post.scheduled_time)
                job_args = {
                    'post_id': post.id,
                    'is_repeating': False
                }

            # Добавляем задачу в планировщик
            self.scheduler.add_job(
                func=self._send_post_job,
                trigger=trigger,
                id=job_id,
                args=[job_args],
                misfire_grace_time=300,  # 5 минут на выполнение просроченной задачи
                replace_existing=True
            )

            logger.info(f"Post {post.id} scheduled for {post.scheduled_time}")

            # Обновляем статус поста в базе данных
            if post.id:
                self.db.update_post_status(post.id, 'scheduled')

            return True

        except Exception as e:
            logger.error(f"Error scheduling post {post.id}: {str(e)}")
            if post.id:
                self.db.update_post_status(
                    post.id,
                    'error',
                    f"Ошибка планирования: {str(e)}"
                )
            return False

    def _create_repeating_trigger(self, post: Post) -> CronTrigger:
        """
        Создание триггера для повторяющихся публикаций

        Args:
            post: Модель поста с информацией о повторении

        Returns:
            CronTrigger для планирования
        """
        # Извлекаем время из запланированной даты
        scheduled_time = post.scheduled_time

        if post.repeat_interval == 'daily':
            # Ежедневно в то же время
            return CronTrigger(
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=scheduled_time.second
            )

        elif post.repeat_interval == 'weekly':
            # Еженедельно в тот же день и время
            return CronTrigger(
                day_of_week=scheduled_time.weekday(),  # 0=понедельник, 6=воскресенье
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=scheduled_time.second
            )

        elif post.repeat_interval == 'monthly':
            # Ежемесячно в тот же день месяца и время
            return CronTrigger(
                day=scheduled_time.day,
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=scheduled_time.second
            )

        else:
            # По умолчанию - ежедневно
            logger.warning(f"Unknown repeat interval '{post.repeat_interval}', using daily")
            return CronTrigger(
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=scheduled_time.second
            )

    def _send_post_job(self, job_args: Dict[str, Any]):
        """
        Задача для отправки запланированного поста

        Args:
            job_args: Аргументы задачи
        """
        post_id = job_args.get('post_id')
        is_repeating = job_args.get('is_repeating', False)

        try:
            logger.info(f"Executing job for post {post_id}")

            # Получаем пост из базы данных
            posts = self.db.get_posts(bot_id=None)  # TODO: передавать bot_id
            post_data = None
            for p in posts:
                if p['id'] == post_id:
                    post_data = p
                    break

            if not post_data:
                logger.error(f"Post {post_id} not found in database")
                return

            post = Post.from_dict(post_data)

            # Проверяем, не истекло ли время повторений
            if is_repeating and post.repeat_until:
                if datetime.now() > post.repeat_until:
                    logger.info(f"Post {post_id} repeat until date reached, stopping")
                    self.scheduler.remove_job(f"post_{post_id}")
                    return

            # Отправляем пост
            self.send_scheduled_posts([post])

            # Для повторяющихся публикаций обновляем счетчик
            if is_repeating and post.repeat_count > 0:
                post.repeat_count -= 1
                if post.repeat_count <= 0:
                    logger.info(f"Post {post_id} repeat count reached, stopping")
                    self.scheduler.remove_job(f"post_{post_id}")

        except Exception as e:
            logger.error(f"Error in job for post {post_id}: {str(e)}")

    def send_scheduled_posts(self, posts: Optional[list] = None) -> Dict[str, Any]:
        """
        Отправка запланированных публикаций

        Args:
            posts: Список постов для отправки (если None, берет из базы)

        Returns:
            Словарь с результатами отправки
        """
        results = {
            'success': 0,
            'error': 0,
            'details': []
        }

        try:
            # Если посты не переданы, получаем запланированные из базы
            if posts is None:
                posts_data = self.db.get_posts(status='scheduled', bot_id=None)
                posts = [Post.from_dict(p) for p in posts_data]

            current_time = datetime.now()

            for post in posts:
                try:
                    # Проверяем, наступило ли время публикации
                    if post.scheduled_time and post.scheduled_time <= current_time:
                        logger.info(f"Sending post {post.id} to channel {post.channel_id}")

                        # Отправляем сообщение
                        message_id = self.telegram_api.send_message(
                            chat_id=post.channel_id,
                            text=post.content,
                            buttons=post.buttons,
                            media_path=post.media_path
                        )

                        if message_id:
                            # Обновляем статус поста
                            self.db.update_post_status(post.id, 'sent')

                            # Удаляем задачу из планировщика для разовых постов
                            if not post.repeat_interval:
                                job_id = f"post_{post.id}"
                                if self.scheduler.get_job(job_id):
                                    self.scheduler.remove_job(job_id)

                            results['success'] += 1
                            results['details'].append({
                                'post_id': post.id,
                                'status': 'success',
                                'message_id': message_id,
                                'timestamp': datetime.now().isoformat()
                            })

                            logger.info(f"Post {post.id} sent successfully (message_id: {message_id})")
                        else:
                            # Ошибка отправки
                            error_msg = "Failed to send message"
                            self.db.update_post_status(post.id, 'error', error_msg)
                            results['error'] += 1
                            results['details'].append({
                                'post_id': post.id,
                                'status': 'error',
                                'error': error_msg
                            })

                            logger.error(f"Failed to send post {post.id}")

                    else:
                        logger.debug(f"Post {post.id} not ready yet (scheduled for {post.scheduled_time})")

                except Exception as e:
                    logger.error(f"Error sending post {post.id}: {str(e)}")

                    # Обновляем статус поста в случае ошибки
                    self.db.update_post_status(post.id, 'error', str(e))

                    results['error'] += 1
                    results['details'].append({
                        'post_id': post.id,
                        'status': 'error',
                        'error': str(e)
                    })

            return results

        except Exception as e:
            logger.error(f"Error in send_scheduled_posts: {str(e)}")
            results['error'] = len(posts) if posts else 1
            return results

    def reschedule_repeating_posts(self):
        """
        Перепланирование повторяющихся публикаций

        Этот метод вызывается при старте приложения для восстановления
        повторяющихся публикаций из базы данных
        """
        try:
            logger.info("Rescheduling repeating posts...")

            # Получаем все активные посты с повторением
            posts_data = self.db.get_posts(status='scheduled', bot_id=None)

            for post_data in posts_data:
                post = Post.from_dict(post_data)

                # Пропускаем посты без повторения
                if not post.repeat_interval:
                    continue

                # Пропускаем посты с истекшим сроком повторения
                if post.repeat_until and datetime.now() > post.repeat_until:
                    continue

                # Пропускаем посты с исчерпанным количеством повторений
                if post.repeat_count <= 0:
                    continue

                # Перепланируем пост
                self.schedule_post(post)

            logger.info(f"Repeating posts rescheduled successfully")

        except Exception as e:
            logger.error(f"Error rescheduling repeating posts: {str(e)}")

    def _check_scheduled_posts_loop(self):
        """
        Фоновый поток для периодической проверки отложенных постов
        """
        logger.info("Background check thread started")

        check_interval = 60  # Проверять каждую минуту

        while self.is_running:
            try:
                # Проверяем и отправляем запланированные посты
                result = self.send_scheduled_posts()

                # Логируем результат если есть что отправлять
                if result['success'] > 0 or result['error'] > 0:
                    logger.info(
                        f"Background check: {result['success']} sent, "
                        f"{result['error']} errors"
                    )

                # Проверяем необходимость перепланирования повторяющихся постов
                # (например, если были изменения в базе данных)
                if self._should_reschedule_repeating_posts():
                    self.reschedule_repeating_posts()

            except Exception as e:
                logger.error(f"Error in background check loop: {str(e)}")

            # Ждем перед следующей проверкой
            time.sleep(check_interval)

    def _should_reschedule_repeating_posts(self) -> bool:
        """
        Проверка необходимости перепланирования повторяющихся постов

        Returns:
            True если требуется перепланирование
        """
        # Здесь можно реализовать логику проверки изменений в базе данных
        # Например, проверять время последнего изменения постов с повторением
        # В текущей реализации всегда возвращаем False
        return False

    def _job_executed(self, event):
        """
        Обработчик событий выполнения задач

        Args:
            event: Событие выполнения задачи
        """
        if event.exception:
            logger.error(f"Job {event.job_id} failed with exception: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")

    def get_scheduled_jobs(self) -> list:
        """
        Получение списка запланированных задач

        Returns:
            Список словарей с информацией о задачах
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

    def cancel_post(self, post_id: int) -> bool:
        """
        Отмена запланированной публикации

        Args:
            post_id: ID поста для отмены

        Returns:
            True если публикация успешно отменена
        """
        try:
            job_id = f"post_{post_id}"

            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Post {post_id} scheduling cancelled")

            # Обновляем статус поста в базе
            self.db.update_post_status(post_id, 'draft')

            return True

        except Exception as e:
            logger.error(f"Error cancelling post {post_id}: {str(e)}")
            return False

    def update_scheduled_post(self, post: Post) -> bool:
        """
        Обновление запланированной публикации

        Args:
            post: Обновленная модель поста

        Returns:
            True если публикация успешно обновлена
        """
        try:
            # Отменяем текущую задачу
            self.cancel_post(post.id)

            # Планируем заново с новыми параметрами
            return self.schedule_post(post)

        except Exception as e:
            logger.error(f"Error updating scheduled post {post.id}: {str(e)}")
            return False


# Создаем глобальный экземпляр планировщика для использования в приложении
_scheduler_instance = None


def get_scheduler(telegram_api=None, database=None) -> Scheduler:
    """
    Получение или создание глобального экземпляра планировщика

    Args:
        telegram_api: Экземпляр TelegramAPI (требуется при первом вызове)
        database: Экземпляр базы данных

    Returns:
        Экземпляр Scheduler
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        if telegram_api is None:
            raise ValueError("telegram_api is required for first scheduler initialization")
        _scheduler_instance = Scheduler(telegram_api, database)

    return _scheduler_instance


def init_scheduler(telegram_api, database=None) -> Scheduler:
    """
    Инициализация и запуск планировщика

    Args:
        telegram_api: Экземпляр TelegramAPI
        database: Экземпляр базы данных

    Returns:
        Экземпляр запущенного Scheduler
    """
    scheduler = get_scheduler(telegram_api, database)
    if not scheduler.is_running:
        scheduler.start()
    return scheduler


if __name__ == "__main__":
    # Пример использования
    import sys

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        token = sys.argv[1]

        # Создаем экземпляры
        api = TelegramAPI(token)
        scheduler = Scheduler(api)

        # Запускаем планировщик
        scheduler.start()

        print("Scheduler started. Press Ctrl+C to stop.")

        try:
            # Демонстрация: получаем список запланированных задач
            while True:
                jobs = scheduler.get_scheduled_jobs()
                print(f"\nActive jobs: {len(jobs)}")
                for job in jobs:
                    print(f"  - {job['id']}: next run at {job['next_run_time']}")

                time.sleep(60)

        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            scheduler.stop()
    else:
        print("Usage: python scheduler.py <bot_token>")
        print("Example: python scheduler.py 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")