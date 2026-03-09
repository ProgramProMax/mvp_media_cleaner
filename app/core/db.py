from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings

engine = create_async_engine(settings.postgres_url, echo=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Return a transactional session as an async context manager.

    This helper is used throughout the codebase both as a dependency in
    FastAPI views and manually with ``async with`` by bot handlers and
    Celery tasks.  The previous implementation returned an async generator
    but was not decorated with :func:`asynccontextmanager`, hence it could not
    be used with ``async with`` and raised
    ``TypeError: 'async_generator' object does not support the asynchronous
    context manager protocol``.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=str(e.orig),
            )
        except SQLAlchemyError as e:
            await session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=str(e.code),
            )
