from pydantic import BaseModel, Field


class UserBase(BaseModel):
    telegram_id: int = Field(...)


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    telegram_id: int = Field(None)


class UserInfo(UserBase):
    id: int
