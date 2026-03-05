from pathlib import Path
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_PATH = BASE_DIR / '.env'


class Settings(BaseSettings):
    # Database
    postgres_user: str = 'postgres'
    postgres_password: str = 'postgres'
    postgres_db: str = 'audio_db'
    postgres_server: str = 'db'
    postgres_port: str = '5432'

    # API Tokens (optional for migration phase)
    telegram_token: Optional[str] = None
    # full HTTPS URL that Telegram will POST updates to.  Typically something
    # like "https://mydomain.com/webhook/<token>".  This value must be set for
    # webhook mode to function; when it is `None` the bot will not attempt to
    # configure the webhook on startup.
    telegram_webhook_url: Optional[str] = None
    openai_token: Optional[str] = None

    host_name: str = 'localhost'

    # Redis
    redis_host: str = 'redis'
    redis_port: str = '6379'
    redis_database: str = '0'

    model_config = ConfigDict(
        env_file='.env',
        case_sensitive=False,
        extra='ignore',
        arbitrary_types_allowed=True,
    )

    @property
    def redis_url(self) -> str:
        return (
            f'redis://{self.redis_host}:'
            f'{self.redis_port}/{self.redis_database}'
        )

    @property
    def postgres_url(self) -> str:
        return (
            f'postgresql+asyncpg://{self.postgres_user}:'
            f'{self.postgres_password}@{self.postgres_server}:'
            f'{self.postgres_port}/{self.postgres_db}'
        )

    model_config = ConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )


settings = Settings()
