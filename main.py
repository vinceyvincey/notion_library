import logging
from fastapi import FastAPI
from markitdown import MarkItDown
import os
from pydantic import BaseModel, field_validator
import re
import sys
from dotenv import load_dotenv
from markdown_conversion import convert_pdf_to_markdown

# Load environment variables from .env file
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler and set level to INFO
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add file handler
file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Prevent duplicate logs
logger.propagate = False


class DriveURL(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_and_format_url(cls, url):
        logger.info(f"Validating URL: {url}")

        if not url:
            logger.error("URL is empty or None")
            raise ValueError("URL cannot be empty")

        file_id_pattern = r"(?:/file/d/|/d/|id=)([a-zA-Z0-9_-]+)"
        match = re.search(file_id_pattern, url)

        if not match:
            logger.error(f"Could not extract file ID from URL: {url}")
            raise ValueError(
                "Could not find a valid Google Drive file ID in the URL. Please ensure you're using a valid Google Drive sharing link."
            )

        file_id = match.group(1)
        logger.info(f"Extracted file ID: {file_id}")
        return file_id


app = FastAPI()
md = MarkItDown()


@app.post("/convert-from-url")
async def convert_from_url(drive_url: DriveURL):
    return convert_pdf_to_markdown(drive_url.url)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Google Drive to Markdown Converter API",
        "usage": "POST a Google Drive URL to /convert-from-url endpoint",
    }
