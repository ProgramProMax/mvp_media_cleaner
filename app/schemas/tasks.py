from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, UUID4


class TaskBase(BaseModel):
    status: str = Field(...)
    original_file_url: str = Field(...)


class TaskCreate(TaskBase):
    status: str | None = Field(None)
    user_id: UUID4


class TaskUpdate(TaskBase):
    status: Optional[str] = Field(
        None
    )
    audio_url: Optional[str] = Field(
        None
    )
    transcript: Optional[str] = Field(None)
    summary_json: Optional[dict] = Field(None)
    cleanned_audio_url: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    finished_at: Optional[datetime] = Field(None)


class TaskInfo(TaskBase):
    id: UUID4
    audio_url: HttpUrl
    transcript: str
    summary_json: dict
    cleanned_audio_url: HttpUrl
    error_message: str
    finished_at: datetime
    created_at: datetime


class TaskCeleryData:
    filename: str | None = Field(None)
    path: Path | None = Field(None)
    file_type: str | None = Field(None)
    file_path: str | None = Field(None)
    audio_path: str | None = Field(None)
    trascribe: dict[str, str | dict[str, float | str]]
    cleaned_text: str = Field(None)
