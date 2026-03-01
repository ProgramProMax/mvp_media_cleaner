from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class TaskBase(BaseModel):
    status: str = Field(...)
    original_file_url: HttpUrl = Field(...)


class TaskCreate(TaskBase):
    user_id: int


class TaskUpdate(TaskBase):
    status: Optional[str] = Field(
        None
    )
    audio_url: Optional[str] = Field(
        None
    )
    transcript: Optional[str] = Field(None)
    summary_json: Optional[dict] = Field(None)
    cleanned_audio_url: Optional[HttpUrl] = Field(None)
    error_message: Optional[str] = Field(None)
    finished_at: Optional[datetime] = Field(None)


class TaskInfo(TaskBase):
    id: int
    audio_url: HttpUrl
    transcript: str
    summary_json: dict
    cleanned_audio_url: HttpUrl
    error_message: str
    finished_at: datetime
    created_at: datetime
