from pydantic import BaseModel


class Segment(BaseModel):
    start: float
    end: float
    text: str


class AudioTrascribe(BaseModel):
    text: str
    segments: list[Segment]


class SummaryAudio(BaseModel):
    short_summary: str
    bullet_points: list
