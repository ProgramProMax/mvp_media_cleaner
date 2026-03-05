from pathlib import Path
import subprocess
import asyncio

import requests
from celery import chain
from celery.signals import task_prerun, task_postrun
from faster_whisper import WhisperModel

from app.core.config import settings
from .celery_app import celery_app, openai
from app.crud.tasks import task_crud
from app.models.tasks import StatusEnum
from app.core.db import get_async_session
from app.core.constants import BASE_DIR, MEDIA_URL_FORMAT, FILTER_WORDS
from app.schemas.tasks import TaskCeleryData, TaskUpdate
from app.schemas.openai import SummaryAudio


async def update_status(task_id: int, status: StatusEnum) -> None:
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, status)


@celery_app.task(bind=True, name='tasks.download_task')
def download_task(self, task_id: int, file_url: str, user_id: int) -> TaskCeleryData:

    asyncio.run(update_status(task_id, StatusEnum.PROCESSING))

    path = BASE_DIR / '.temp'
    path.mkdir(exist_ok=True)

    response = requests.get(file_url)
    file_type = file_url.rsplit('.')[-1]
    file_name = f'{task_id}-{user_id}'
    file_path = path / f'{file_name}.{file_type}'

    with open(file_path, 'wb') as file:
        file.write(response.content)

    return TaskCeleryData(
        filename=file_name,
        path=path,
        file_path=file_path,
        file_type=file_type
    )


@celery_app.task(bind=True, name='tasks.extract_audio_task')
def extract_audio_task(self, task_id: int, download_data: TaskCeleryData):

    if download_data.file_type in ['mov', 'mp4']:
        command = [
            'ffmpeg',
            '-i',
            download_data.file_path,
            '-ar',
            '16000',
            '-ac',
            '1',
            BASE_DIR / f'media/{download_data.filename}.wav'
        ]
        subprocess.call(command)
        obj_in = TaskUpdate(
            audio_url=MEDIA_URL_FORMAT.format(
                f'{download_data.filename}.wav'
            )
        )
        download_data.audio_path = BASE_DIR / 'media' / f'{download_data.filename}.wav'
    else:
        obj_in = TaskUpdate(
            audio_url=MEDIA_URL_FORMAT.format(
                f'{download_data.filename}.{download_data.file_type}'
            )
        )
        download_data.audio_path = download_data.file_path
    asyncio.run(task_crud.update_by_id(task_id, obj_in))
    return download_data


@celery_app.task(bind=True, name='tasks.transcribe_task')
def trancribe_task(self, task_id: int, data: TaskCeleryData):
    asyncio.run(update_status(task_id, StatusEnum.TRANSCRIBING))
    model = WhisperModel('base', device='cpu')
    segments, info = model.transcribe(data.file_path)

    result = {
        "text": "",
        "segments": []
    }

    for segment in segments:
        result["segments"].append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        })
        result["text"] += segment.text.strip() + " "

    result["text"] = result["text"].strip()
    data.trascribe = result
    return data


@celery_app.task(bind=True, name='tasks.clean_text_task')
def clean_text_task(self, task_id: int, data: TaskCeleryData):
    asyncio.run(update_status(task_id, StatusEnum.CLEANING))
    response = openai.chat.completions.create(
        model='gpt-4o',
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional editor. Remove filler words from the transcript. "
                    f"Filler words list: {', '.join(FILTER_WORDS)}. "
                    "Constraints: Do NOT change meaning. Do NOT rephrase. "
                    "Fix capitalization/punctuation if needed after removal. "
                    "Output ONLY the cleaned text, no markdown or explanations."
                )
            },
            {
                "role": "user",
                "content": data.trascribe['text']
            }
        ],
        max_tokens=4000,
        timeout=30,
    )
    data.cleaned_text = response.choices[0].message.content
    asyncio.run(task_crud.update_status())
    return data


@celery_app.task(bind=True, name='tasks.summarize_task')
def summarize_task(self, task_id: int, data: TaskCeleryData):
    asyncio.run(update_status(task_id, StatusEnum.CLEANING))
    response = openai.chat.completions.create(
        model='gpt-4o',
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an executive assistant. Create a summary of the transcript."
                )
            },
            {
                "role": "user",
                "content": (f"Create a summary based on this text:\n\n{data.cleaned_text}\n\n"
                        "Required JSON Schema:\n"
                        "{\n"
                        '  "short_summary": "String (5-7 sentences)",\n'
                        '  "bullet_points": ["String", "String", "..."]\n'
                        "}"
                )
            }
        ],
        response_format=SummaryAudio,
        max_tokens=4000,
        timeout=30,
    )
    data.cleaned_text = response.choices[0].message.content
    asyncio.run(task_crud.update_status())
    summary = {'summary': 'краткое содержание...'}
    return summary


@celery_app.task(bind=True, name='tasks.rebuild_audio_task')
def rebuild_audio_task(self, task_id: int, data: dict):
    # TODO переписать
    await update_status(task_id, StatusEnum.BUILDING_AUDIO)
    # pretend we generated a new audio file or url
    audio_url = 'http://example.com/generated.mp3'
    return {'audio_url': audio_url}


@celery_app.task(bind=True, name='tasks.finalize_task')
def finalize_task(self, task_id: int, data: dict):
    # TODO переписать
    await update_status(task_id, StatusEnum.DONE)
    return {'status': 'completed'}


@celery_app.task(bind=True, name='tasks.process_media_chain')
def process_media_chain(
    self,
    task_id: int,
    file_url: str,
    user_id: int
):
    print(f"🔗 Process chain task ID: {self.request.id}")
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
    print(f"Chain started with ID: {result.id}")
    return {
        'task_id': task_id,
        'chain_id': result.id,
        'status': 'started'
    }



@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    print(f"🚀 [{task.name}] Task started - ID: {task_id}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, **kwargs):
    print(f"✅ [{task.name}] Task completed - ID: {task_id}")
