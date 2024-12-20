import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
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

API_KEY = os.getenv("SERVICE_API_KEY")
API_KEY_NAME = "access-token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


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

# Configure CORS
origins = [
    "https://www.notion.so",  # Add Notion's origin
    # Add other origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

md = MarkItDown()


async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


@app.post("/convert-from-url")
async def convert_from_url(drive_url: DriveURL, api_key: str = Depends(get_api_key)):
    return convert_pdf_to_markdown(drive_url.url)


@app.post("/notion-webhook")
async def notion_webhook(request: Request, api_key: str = Depends(get_api_key)):
    try:
        payload = await request.json()
        # Navigate through the JSON structure to find the URL
        files = (
            payload.get("data", {})
            .get("properties", {})
            .get("File", {})
            .get("files", [])
        )
        if not files:
            raise HTTPException(status_code=400, detail="No files found in the request")

        # Assuming the first file is the one we want
        file_info = files[0]
        drive_url = file_info.get("external", {}).get("url")
        if not drive_url:
            raise HTTPException(
                status_code=400, detail="No valid URL found in the file information"
            )

        # Call the conversion function
        return convert_pdf_to_markdown(drive_url)

    except Exception as e:
        logger.error(f"Error processing Notion webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process Notion webhook")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Google Drive to Markdown Converter API",
        "usage": "POST a Google Drive URL to /convert-from-url endpoint",
    }
