from aiogram import Bot
from celery import Celery
from kombu import Exchange, Queue
from openai import OpenAI

from app.core.config import settings

openai = OpenAI(api_key=settings.openai_token)


async def notify_user_task_completed(
    user_id: int,
    task_id: int,
    data: dict
) -> None:
    """
    Оповещает пользователя о выполнении цепочки задач
    Args:
        user_id: ID пользователя в Telegram
        task_id: ID задачи в базе данных
        data: Данные из TaskCeleryData с результатами обработки
    """
    bot = Bot(token=settings.telegram_token)

    summary = data.get('summary_json', {})
    if isinstance(summary, str):
        import json
        try:
            summary = json.loads(summary)
        except json.JSONDecodeError:
            summary = {}

    short_summary = summary.get('short_summary', 'Краткое резюме отсутствует')
    bullet_points = summary.get('bullet_points', [])

    message = (
        f'✅ Задача №{task_id} выполнена!\n\n'
        f'📋 Краткое резюме:\n'
        f'{short_summary}\n\n'
    )

    if bullet_points:
        message += '📌 Основные моменты:\n'
        for i, point in enumerate(bullet_points, 1):
            message += f'{i}. {point}\n'

    message += (
        f'\n🔊 Оригинальное аудио: {data.get("audio_url", "N/A")}\n'
        f'🔊 Очищенное аудио: {data.get("cleanned_audio_url", "N/A")}'
    )

    try:
        await bot.send_message(chat_id=user_id, text=message)
    except Exception as e:
        print(f'Ошибка при отправке уведомления: {e}')
    finally:
        await bot.session.close()

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.celery.celery_tasks"],
)

celery_app.conf.update(
    task_time_limit=1200,
    worker_concurrency=4,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_queues=[
        Queue('celery', Exchange('celery'), routing_key='celery'),
        Queue('download', Exchange('download'), routing_key='download'),
        Queue('audio', Exchange('audio'), routing_key='audio'),
        Queue('transcribe', Exchange('transcribe'), routing_key='transcribe'),
        Queue('text', Exchange('text'), routing_key='text'),
        Queue('summarize', Exchange('summarize'), routing_key='summarize'),
        Queue('rebuild', Exchange('rebuild'), routing_key='rebuild'),
        Queue('finalize', Exchange('finalize'), routing_key='finalize'),
    ],
    task_routes={
        'tasks.download_task': {'queue': 'download'},
        'tasks.extract_audio_task': {'queue': 'audio'},
        'tasks.transcribe_task': {'queue': 'transcribe'},
        'tasks.clean_text_task': {'queue': 'text'},
        'tasks.summarize_task': {'queue': 'summarize'},
        'tasks.rebuild_audio_task': {'queue': 'rebuild'},
        'tasks.finalize_task': {'queue': 'finalize'},
    },
)

user_active_tasks: dict[int, int] = {}


def check_user_task_limit(user_id, max_concurrent_tasks=2) -> bool:
    """
    Проверяет лимит одновременных задач для пользователя
    """
    current_tasks = user_active_tasks.get(user_id, 0)
    if current_tasks >= max_concurrent_tasks:
        raise Exception(
            f'User {user_id} has reached maximum'
            ' concurrent tasks limit'
        )
    user_active_tasks[user_id] = current_tasks + 1
    return True


def release_user_task(user_id) -> None:
    """
    Освобождает слот задачи пользователя
    """
    if user_id in user_active_tasks:
        user_active_tasks[user_id] = max(0, user_active_tasks[user_id] - 1)
        if user_active_tasks[user_id] == 0:
            del user_active_tasks[user_id]
