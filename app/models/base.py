from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, UUID


class Base(DeclarativeBase):
    '''Базовая модель для всех остальных моделей.'''
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
