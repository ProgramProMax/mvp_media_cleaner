from pathlib import Path

from .config import settings

SUPPERTED_FORMATS: tuple[str] = (
    'audio/mpeg',
    'audio/x-wav',
    'audio/x-m4a',
    'video/mp4',
    'video/quicktime'
)
TELEGRAM_FILE_URL_FORMAT: str = 'https://api.telegram.org/file/bot{}/{}'

FILE_MAX_DURATION: int = 3600
MAX_FILE_SIZE: int = 200_000_000


BASE_DIR: Path = Path(__file__).parent.parent
MEDIA_URL_FORMAT: str = 'https://' + settings.host_name + '/media/{}'
FILTER_WORDS: tuple[str] = (
    "эээ", "ммм", "типа", "короче", "значит", "ну", "как бы",
    "uh", "um", "you know", "like", "actually"
)

OPENAI_MAX_TOKENS: int = 4000
OPENAI_TIMEOUT: int = 30
OPENAI_TEMPUTURE: float = 0.3
