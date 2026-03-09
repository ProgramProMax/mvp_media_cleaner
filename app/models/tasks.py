from enum import Enum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String

from .base import Base


class StatusEnum(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    CLEANING = "cleaning"
    SUMMARIZING = "summarizing"
    BUILDING_AUDIO = "building_audio"
    DONE = "done"
    ERROR = "error"


class Task(Base):
    __tablename__ = 'tasks'

    user_id = Column(ForeignKey(
        'users.id', ondelete='CASCADE'
        ),
        nullable=False
    )
    status = Column(
        String,
        nullable=False,
        default=StatusEnum.PENDING.value
    )
    original_file_url = Column(String, nullable=False)
    audio_url = Column(String)
    transcript = Column(String)
    summary_json = Column(JSON)
    cleanned_audio_url = Column(String)
    error_message = Column(String)
    finished_at = Column(DateTime)
