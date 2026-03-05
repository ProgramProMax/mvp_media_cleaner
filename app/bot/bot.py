import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.enums.parse_mode import ParseMode

from app.celery.celery_tasks import process_media_chain
from app.core.config import settings
from app.schemas.users import UserCreate
from app.schemas.tasks import TaskCreate
from app.crud import user_crud, task_crud
from app.core.db import get_async_session
from app.core.constants import SUPPERTED_FORMATS, TELEGRAM_FILE_URL_FORMAT

bot = Bot(token=settings.telegram_token)
dp = Dispatcher()


async def notification_by_task(task_id: int, celery_id: int, timeout: int = 15):
    pass
    # while True:
    #    print('Обработка...')


async def media_check(message: Message):
    '''Обрадотка оправки медиа файла'''
    if message.audio.duration >= 3600:
        await message.answer('Отправленное аудио по длительности более часа')
        return
    if message.audio.mime_type not in SUPPERTED_FORMATS:
        await message.answer('Отправленнoe аудио файл не поддерживается')
        return
    file = await bot.get_file(message.audio.file_id)
    await message.answer("Файл получен")
    print(file.file_path, settings.telegram_token)
    file_url = TELEGRAM_FILE_URL_FORMAT.format(
        settings.telegram_token,
        file.file_path
    )
    async with get_async_session() as session:
        user = await user_crud.get_by_telegram_id(session, message.chat.id)
        taks_obj = TaskCreate(
            original_file_url=file_url,
            user_id=user.id
        )
        task = await task_crud.create(session, taks_obj)

    result = process_media_chain.delay(
        task_id=task.id,
        file_url=file_url,
        user_id=message.chat.id
    )
    print(result.id)
    asyncio.create_task(notification_by_task(task.id, None))
    await message.answer(f'Номер задачи: `{task.id}`', parse_mode=ParseMode.MARKDOWN_V2)


@dp.message(F.audio)
async def audiofile_handler(message: Message):
    await media_check(message)


@dp.message(F.voice)
async def voicefile_handler(message: Message):
    await media_check(message)


@dp.message(Command(commands=["help"]))
async def help_handler(message: Message):
    await message.answer(
        'Описание команд и их работа:\n'
        '`/status <task_id>` - получение статуса задачи\n'
        '`/new` - очищение контекста\n'
        'Для начало обработки отправте аудио или видео '
        'длительностью не более 1 часа и следующих форматов:'
        'mp3, wav, m4a, mp4, mov'
    )


@dp.message(Command(commands=["status"]))
async def status_handler(message: Message, command: CommandObject):
    args = command.args.strip()
    if not args:
        await message.answer('Введите id задачи или celery task id')
        return

    # try to interpret argument as database task id first
    status_text = None

    async with get_async_session() as session:
        db_task = await task_crud.get(session, int(args)) if args.isdigit() else None
        if db_task and getattr(db_task, "celery_task_id", None):
            celery_id = db_task.celery_task_id
        elif db_task:
            celery_id = None
        else:
            celery_id = args  # treat the provided value as a celery id

    if celery_id:
        from celery.result import AsyncResult
        from app.celery.celery_app import celery_app

        result = AsyncResult(celery_id, app=celery_app)
        status_text = f"Celery status for `{celery_id}`: {result.status}"
    elif db_task:
        status_text = f"Task {db_task.id} status: {db_task.status}"
    else:
        status_text = "Задача не найдена"

    await message.answer(status_text)


@dp.message(Command(commands=["new"]))
async def new_handler(message: Message):
    await message.answer("This is a new command handler!")


@dp.message(Command(commands=["start"]))
async def start_handler(message: Message):
    obj_in = UserCreate(
        telegram_id=message.chat.id
    )
    async with get_async_session() as session:
        await user_crud.create(session, obj_in)
    await message.answer("Hello, I'm a Telegram bot!")


async def set_webhook(url: str) -> None:
    """Configure Telegram to send updates to ``url``.

    The URL should include the bot token (or be validated separately by the
    receiving endpoint).  Telegram requires an HTTPS endpoint in production.
    """
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url)


async def delete_webhook() -> None:
    """Remove any existing webhook configuration."""
    await bot.delete_webhook()
