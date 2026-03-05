from pathlib import Path

from .config import settings

SUPPERTED_FORMATS: tuple[str] = (
    'audio/mpeg',
    'audio/x-wav',
    'audio/x-m4a',
    'video/mp4',
    'video/quicktime'
)
TELEGRAM_FILE_URL_FORMAT = 'https://api.telegram.org/file/bot{}/{}'
BASE_DIR = Path(__file__).parent.parent
MEDIA_URL_FORMAT = 'https://' + settings.host_name + '/media/{}'
FILTER_WORDS = [
    "эээ", "ммм", "типа", "короче", "значит", "ну", "как бы",
    "uh", "um", "you know", "like", "actually"
]
