import requests
from pathlib import Path
from celery import chain

from .celery_app import celery_app
from app.crud.tasks import task_crud
from app.models.tasks import StatusEnum
from app.core.db import get_async_session


@celery_app.task(blind=True, name='tasks.download_task')
async def download_task(self, task_id: int, file_url: str, user_id: int) -> dict:
    # mark task as processing
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.PROCESSING)
    path = Path(__file__).parent.parent
    path.mkdir('.temp', exist_ok=True)

    response = requests.get(file_url)
    file_type = file_url.rsplit('.')[-1]
    file_name = f'{task_id}-{user_id}.{file_type}'
    with open(f'{path}{file_name}', 'wb') as file:
        file.write(response.content)

    return {
        'file_path': ''
    }


@celery_app.task(blind=True, name='tasks.extract_audio_task')
async def extract_audio_task(self, task_id: int, download_data: dict):
    # usually convert video to audio, etc.
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.PROCESSING)
    # stub implementation: just forward the downloaded file name
    audio_path = download_data.get('file_name')
    return {'audio_path': audio_path}


@celery_app.task(blind=True, name='tasks.transcribe_task')
async def trancribe_task(self, task_id: int, data: dict):
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.TRANSCRIBING)
    # stub: pretend transcription happened
    transcript = '...text from audio...'
    return {'transcript': transcript}


@celery_app.task(blind=True, name='tasks.clean_text_task')
async def clean_text_task(self, task_id: int, data: dict):
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.CLEANING)
    # remove filler words, etc.
    cleaned = data.get('transcript', '')
    return {'cleaned': cleaned}


@celery_app.task(blind=True, name='tasks.summarize_task')
async def summarize_task(self, task_id: int, data: dict):
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.SUMMARIZING)
    # create a simple summary
    summary = {'summary': 'краткое содержание...'}
    return summary


@celery_app.task(blind=True, name='tasks.rebuild_audio_task')
async def rebuild_audio_task(self, task_id: int, data: dict):
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.BUILDING_AUDIO)
    # pretend we generated a new audio file or url
    audio_url = 'http://example.com/generated.mp3'
    return {'audio_url': audio_url}


@celery_app.task(blind=True, name='tasks.finalize_task')
async def finalize_task(self, task_id: int, data: dict):
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, StatusEnum.DONE)
        # optionally record final pieces like audio_url/transcript/etc
        await task_crud.update(session, await session.get(task_crud.model, task_id), data)
    return {'status': 'completed'}


@celery_app.task(blind=True)
def process_media_chain(
    self,
    task_id: int,
    file_url: str,
    user_id: int
):
    workflow = chain(
        download_task.s(task_id, file_url, user_id) |
        extract_audio_task.s(task_id) |
        trancribe_task.s(task_id) |
        clean_text_task.s(task_id) |
        summarize_task.s(task_id) |
        rebuild_audio_task.s(task_id) |
        finalize_task.s(task_id)
    )
    result = workflow.apply_async()

    return {
        'task_id': task_id,
        'chain_id': result.id,
        'status': 'started'
    }
