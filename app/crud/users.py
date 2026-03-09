from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from .base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    async def create(
        self,
        session: AsyncSession,
        obj_in: UserCreate
    ) -> User:
        user = await self.get_by_telegram_id(session, obj_in.telegram_id)
        if user:
            return user
        return await super().create(session, obj_in)

    async def get_by_telegram_id(
        self,
        session: AsyncSession,
        telegram_id: int
    ) -> Optional[User]:
        user = await session.execute(
            select(self.model).where(self.model.telegram_id == telegram_id)
        )
        return user.scalar_one_or_none()


user_crud = CRUDUser(User)
