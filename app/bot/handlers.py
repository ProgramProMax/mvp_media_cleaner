from aiogram import Bot, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import Command, CommandObject, ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Audio, Document, ErrorEvent, Message, Voice

from app.celery.celery_app import check_user_task_limit
from app.celery.celery_tasks import process_media_chain
from app.core.config import settings
from app.core.constants import SUPPERTED_FORMATS, TELEGRAM_FILE_URL_FORMAT, MAX_FILE_SIZE, FILE_MAX_DURATION
from app.core.db import get_async_session
from app.crud import task_crud, user_crud
from app.schemas.tasks import TaskCreate
from app.schemas.users import UserCreate
from .bot import bot, dp


class InvalidMediaFormat(Exception):
    message = None

    def __init__(self, message: str) -> None:
        self.message = message


@dp.errors(ExceptionTypeFilter(InvalidMediaFormat))
async def media_fomat_handler(
    event: ErrorEvent,
    bot: Bot
) -> bool:
    await bot.send_message(
        chat_id=event.update.message.chat.id,
        text=event.exception.message
    )
    return True


async def media_check(message: Message, file: Audio | Voice | Document):
    '''Обрадотка оправки медиа файла'''
    if file.duration >= FILE_MAX_DURATION:
        raise ExceptionTypeFilter(
            'Отправленное аудио по длительности более часа'
        )
    if file.mime_type not in SUPPERTED_FORMATS:
        raise ExceptionTypeFilter('Отправленнoe аудио файл не поддерживается')
    if file.file_size >= MAX_FILE_SIZE:
        raise ExceptionTypeFilter('Отправленнoe аудио файл слишком большой')

    file_info = await bot.get_file(file.file_id)
    await message.answer("Файл получен")
    file_url = TELEGRAM_FILE_URL_FORMAT.format(
        settings.telegram_token,
        file_info.file_path
    )
    async with get_async_session() as session:
        user = await user_crud.get_by_telegram_id(session, message.chat.id)
        taks_obj = TaskCreate(
            original_file_url=file_url,
            user_id=user.id
        )
        task = await task_crud.create(session, taks_obj)
    check_user_task_limit(message.chat.id)
    process_media_chain.delay(
        task_id=task.id,
        file_url=file_url,
        user_id=message.chat.id
    )
    await message.answer(
        f'Номер задачи: `{task.id}`',
        parse_mode=ParseMode.MARKDOWN_V2
    )


@dp.message(F.voice | F.audio | F.doument)
async def media_handler(message: Message, state: FSMContext):
    if message.audio:
        await media_check(message, message.audio)
    elif message.voice:
        await media_check(message, message.voice)
    elif message.document:
        await media_check(message, message.document)


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

    status = None

    async with get_async_session() as session:
        db_task = await (
            task_crud.get(session, int(args))
            if args.isdigit() else None
        )
        if db_task:
            status = db_task.status
    if status:
        await message.answer(f"Задача №{db_task.id} статус: {db_task.status}")
        return
    await message.answer('Задача не найдена')


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
