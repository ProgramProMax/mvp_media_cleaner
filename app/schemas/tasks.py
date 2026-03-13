from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import UUID4, BaseModel, Field, HttpUrl

from .openai import SummaryAudio


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


class TaskCeleryData(BaseModel):
    filename: Optional[str] = Field(None)
    path: Optional[str] = Field(None)
    file_type: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None)
    audio_url: Optional[str] = Field(None)
    audio_path: Optional[str] = Field(None)
    cleaned_audio_url: Optional[str] = Field(None)
    cleaned_audio_path: Optional[str] = Field(None)
    trascribe: Optional[dict] = Field(None)
    cleaned_text: Optional[str] = Field(None)
    summary_json: Optional[SummaryAudio] = Field(None)
