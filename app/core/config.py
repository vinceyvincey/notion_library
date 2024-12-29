import sys
from functools import lru_cache

from dotenv import load_dotenv
from loguru import logger
from pydantic_settings import BaseSettings

load_dotenv()  # Load environment variables from .env


class Settings(BaseSettings):
    app_name: str = "Notion Library"
    debug: bool = False
    service_api_key: str
    openrouter_api_key: str | None = None

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


def setup_logging(debug: bool = False):
    # Remove default logger
    logger.remove()

    # Add stdout handler with custom format
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Set log level based on debug flag
    log_level = "DEBUG" if debug else "INFO"

    # Add console handler
    logger.add(sys.stdout, format=log_format, level=log_level, colorize=True)

    # Add file handler for all levels
    logger.add(
        "app.log",
        format=log_format,
        level="DEBUG",
        rotation="500 MB",
        retention="10 days",
    )
