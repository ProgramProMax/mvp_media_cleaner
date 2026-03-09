import asyncio
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response

from app.bot.bot import bot, delete_webhook, dp, set_webhook
from app.core.config import settings
from .api.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.telegram_webhook_url:
        # configure telegram webhook with the provided URL
        await set_webhook(settings.telegram_webhook_url)
    asyncio.create_task(dp.start_polling(bot))
    yield
    if settings.telegram_webhook_url:
        await delete_webhook()


app = FastAPI(lifespan=lifespan)

telegram_router = APIRouter()


@telegram_router.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    """Endpoint that receives updates from Telegram.

    The path contains the bot token for a basic level of security; we also
    verify it matches the configured token.
    """
    if not settings.telegram_token or token != settings.telegram_token:
        raise HTTPException(status_code=403, detail="Invalid token")

    body = await request.json()
    update = Update(**body)
    await dp.process_update(update)
    return Response(status_code=200)

app.include_router(telegram_router)
app.include_router(api_router)
