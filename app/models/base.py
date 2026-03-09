from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, Column, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    '''Базовая модель для всех остальных моделей.'''
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
