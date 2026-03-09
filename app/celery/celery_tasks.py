import asyncio
import subprocess

import requests
from celery import chain
from faster_whisper import WhisperModel

from app.core.constants import (
    BASE_DIR,
    FILTER_WORDS,
    MEDIA_URL_FORMAT,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPUTURE,
    OPENAI_TIMEOUT,
)
from app.core.db import get_async_session
from app.crud.tasks import task_crud
from app.models.tasks import StatusEnum
from app.schemas.openai import SummaryAudio
from app.schemas.tasks import TaskCeleryData, TaskUpdate
from .celery_app import celery_app, openai, check_user_task_limit, release_user_task


async def update_status(task_id: int, status: StatusEnum) -> None:
    async with get_async_session() as session:
        await task_crud.update_status(session, task_id, status)


async def update_task_by_id(task_id: int, obj_in: TaskUpdate) -> None:
    async with get_async_session() as session:
        await task_crud.update_by_id(session, task_id, obj_in)


@celery_app.task(bind=True, name='tasks.download_task')
def download_task(
    self,
    task_id: int,
    file_url: str,
    user_id: int
) -> TaskCeleryData:

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
def extract_audio_task(
    self,
    task_id: int,
    download_data: TaskCeleryData
) -> TaskCeleryData:

    if download_data.file_type in ['mov', 'mp4']:
        output_path = BASE_DIR / 'media' / f'{download_data.filename}.wav'
        command = [
            'ffmpeg',
            '-i',
            download_data.file_path,
            '-ar',
            '16000',
            '-ac',
            '1',
            output_path
        ]
        subprocess.call(command)
        obj_in = TaskUpdate(
            audio_url=MEDIA_URL_FORMAT.format(
                f'{download_data.filename}.wav'
            )
        )
        download_data.audio_path = output_path
    else:
        download_data.audio_url = MEDIA_URL_FORMAT.format(
                f'{download_data.filename}.{download_data.file_type}'
            )
        download_data.audio_path = download_data.file_path
    asyncio.run(task_crud.update_by_id(task_id, obj_in))
    return download_data


@celery_app.task(bind=True, name='tasks.transcribe_task')
def trancribe_task(
    self,
    task_id: int,
    data: TaskCeleryData
) -> TaskCeleryData:
    asyncio.run(update_status(task_id, StatusEnum.TRANSCRIBING))
    model = WhisperModel('base', device='cpu')
    segments, _ = model.transcribe(data.file_path)

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
def clean_text_task(
    self,
    task_id: int,
    data: TaskCeleryData
) -> TaskCeleryData:
    asyncio.run(update_status(task_id, StatusEnum.CLEANING))
    response = openai.chat.completions.create(
        model='gpt-4o',
        temperature=OPENAI_TEMPUTURE,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional editor. Remove filler words"
                    " from the transcript. "
                    f"Filler words list: {', '.join(FILTER_WORDS)}. "
                    "Constraints: Do NOT change meaning. Do NOT rephrase. "
                    "Fix capitalization/punctuation if needed after removal. "
                    "Output ONLY the cleaned text, no markdown or "
                    "explanations."
                )
            },
            {
                "role": "user",
                "content": data.trascribe['text']
            }
        ],
        max_tokens=OPENAI_MAX_TOKENS,
        timeout=OPENAI_TIMEOUT,
    )
    data.cleaned_text = response.choices[0].message.content
    asyncio.run(task_crud.update_status())
    return data


@celery_app.task(bind=True, name='tasks.summarize_task')
def summarize_task(
    self,
    task_id: int,
    data: TaskCeleryData
) -> TaskCeleryData:
    asyncio.run(update_status(task_id, StatusEnum.CLEANING))
    response = openai.chat.completions.create(
        model='gpt-4o',
        temperature=OPENAI_TEMPUTURE,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an executive assistant. "
                    "Create a summary of the transcript."
                )
            },
            {
                "role": "user",
                "content": (
                    "Create a summary based on this text:"
                    f"\n\n{data.cleaned_text}\n\n"
                    "Required JSON Schema:\n"
                    "{\n"
                    '  "short_summary": "String (5-7 sentences)",\n'
                    '  "bullet_points": ["String", "String", "..."]\n'
                    "}"
                )
            }
        ],
        response_format=SummaryAudio,
        max_tokens=OPENAI_MAX_TOKENS,
        timeout=OPENAI_TIMEOUT,
    )
    data.summary_json = response
    return data


@celery_app.task(bind=True, name='tasks.rebuild_audio_task')
def rebuild_audio_task(
    self,
    task_id: int,
    data: TaskCeleryData
) -> TaskCeleryData:
    asyncio.run(update_status(task_id, StatusEnum.BUILDING_AUDIO))

    try:
        # Получаем сегменты транскрипции
        segments = data.trascribe.get('segments', [])

        # Фильтруем сегменты, удаляя те, которые содержат filler words
        filtered_segments = []
        for segment in segments:
            segment_text = segment.get('text', '').lower().strip()
            # Проверяем, содержит ли сегмент filler words
            if not any(filler in segment_text for filler in FILTER_WORDS):
                filtered_segments.append(segment)

        if not filtered_segments:
            # Если нет сегментов после фильтрации,
            # используем оригинальное аудио
            data.cleaned_audio_url = data.audio_url
            data.cleaned_audio_path = data.audio_path
            return data

        # Создаём список команд для ffmpeg для склеивания аудио
        audio_parts = []
        temp_dir = BASE_DIR / '.temp'
        temp_dir.mkdir(exist_ok=True)

        # Извлекаем аудио по таймкодам
        for i, segment in enumerate(filtered_segments):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            duration = end - start

            if duration <= 0:
                continue

            # Извлекаем часть аудио
            part_path = temp_dir / f'{data.filename}_part_{i}.wav'
            command = [
                'ffmpeg',
                '-i', data.audio_path,
                '-ss', str(start),
                '-t', str(duration),
                '-acodec', 'copy',
                str(part_path),
                '-y'
            ]
            subprocess.run(command, check=True, capture_output=True)
            audio_parts.append(part_path)

        if not audio_parts:
            data.cleaned_audio_url = data.audio_url
            data.cleaned_audio_path = data.audio_path
            return data

        # Склеиваем все части через ffmpeg
        output_path = BASE_DIR / 'media' / f'{data.filename}_rebuilt.mp3'
        output_path.parent.mkdir(exist_ok=True)

        # Создаём файл со списком частей для ffmpeg
        list_file = temp_dir / 'concat_list.txt'
        with open(list_file, 'w') as f:
            for part_path in audio_parts:
                f.write(f"file '{part_path}'\n")

        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-acodec', 'libmp3lame',
            str(output_path),
            '-y'
        ]
        subprocess.run(command, check=True, capture_output=True)

        for part_path in audio_parts:
            part_path.unlink(missing_ok=True)
        list_file.unlink(missing_ok=True)

        data.cleaned_audio_url = MEDIA_URL_FORMAT.format(
            f'{data.filename}_rebuilt.mp3'
        )
        data.cleaned_audio_path = output_path
        return data

    except subprocess.CalledProcessError as e:
        asyncio.run(task_crud.update_status(task_id, StatusEnum.ERROR))
        raise Exception(f"FFmpeg error: {e.stderr}")


@celery_app.task(bind=True, name='tasks.finalize_task')
def finalize_task(
    self,
    task_id: int,
    user_id: int,
    data: TaskCeleryData
) -> TaskCeleryData:
    asyncio.run(update_status(task_id, StatusEnum.DONE))
    release_user_task(user_id)

    return {'status': 'completed'}


@celery_app.task(bind=True, name='tasks.process_media_chain')
def process_media_chain(
    self,
    task_id: int,
    file_url: str,
    user_id: int,
) -> dict:
    workflow = chain(
        download_task.s(task_id, file_url, user_id) |
        extract_audio_task.s(task_id) |
        trancribe_task.s(task_id) |
        clean_text_task.s(task_id) |
        summarize_task.s(task_id) |
        rebuild_audio_task.s(task_id) |
        finalize_task.s(task_id, user_id)
    )
    result = workflow.apply_async()
    return {
        'task_id': task_id,
        'chain_id': result.id,
        'status': 'started'
    }


