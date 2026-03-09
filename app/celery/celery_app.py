from celery import Celery
from kombu import Exchange, Queue
from openai import OpenAI
from celery.signals import task_postrun, task_prerun

from app.core.config import settings


openai = OpenAI(settings.openai_token)

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
