from fastapi import FastAPI, Request, Response, APIRouter, HTTPException
import asyncio
from contextlib import asynccontextmanager
from aiogram.types import Update

from .api.routers import api_router
from app.bot.bot import dp, set_webhook, delete_webhook, bot
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.telegram_webhook_url:
        # configure telegram webhook with the provided URL
        await set_webhook(settings.telegram_webhook_url)
    asyncio.create_task(dp.start_polling(bot))
    yield
    if settings.telegram_webhook_url:
        await delete_webhook()
    '''
    else:
        # no webhook configured; fall back to polling for development and
        # local docker runs.  polling will run in a background task so that
        # the application can continue handling HTTP requests.
        asyncio.create_task(dp.start_polling(bot))
    '''


app = FastAPI(lifespan=lifespan)

# --- include existing routers ------------------------------------------------
main_router = APIRouter()
main_router.include_router(api_router)
app.include_router(main_router)


# minimal router just to keep code organised
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
