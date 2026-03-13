from aiogram import Bot, Dispatcher

from app.core.config import settings
from .handlers import router

bot = Bot(token=settings.telegram_token)
dp = Dispatcher()

dp.include_router(router)


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
