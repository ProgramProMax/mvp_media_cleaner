from sqlalchemy import Column, Integer

from .base import Base


class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(Integer, unique=True, nullable=False)
