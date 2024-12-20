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
from make_notion_block import NotionBlockMaker

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
        logger.info(f"Received Notion webhook payload: {payload}")

        # Get the page ID from the payload
        page_id = payload.get("data", {}).get("id")
        if not page_id:
            raise HTTPException(
                status_code=400, detail="No page ID found in the request"
            )

        logger.info(f"Extracted page ID: {page_id}")

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
        drive_url = file_info.get("external", {}).get("url", "").strip(";")

        if not drive_url:
            raise HTTPException(
                status_code=400, detail="No valid URL found in the file information"
            )

        logger.info(f"Original URL from Notion: {drive_url}")

        # Extract file ID only if it hasn't been processed yet
        if not drive_url.startswith("https://drive.google.com/uc"):
            # Extract the file ID and construct a direct download link
            file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", drive_url)
            if file_id_match:
                file_id = file_id_match.group(1)
                drive_url = f"https://drive.google.com/uc?id={file_id}"
                logger.info(f"Processed URL: {drive_url}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract valid Google Drive file ID from URL",
                )

        # Convert PDF to markdown
        try:
            result = convert_pdf_to_markdown(drive_url)
        except Exception as e:
            logger.error(f"Error converting PDF: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to convert PDF. Please ensure the Google Drive file is publicly accessible.",
            )

        if not result or "text_content" not in result:
            raise HTTPException(
                status_code=500, detail="Failed to convert PDF to markdown"
            )

        # Create Notion blocks from the markdown content
        notion_maker = NotionBlockMaker()
        success = notion_maker.create_blocks_from_markdown(
            page_id, result["text_content"]
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to create Notion blocks"
            )

        return {"status": "success", "message": "Content added to Notion page"}

    except Exception as e:
        logger.error(f"Error processing Notion webhook: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to process Notion webhook")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Google Drive to Markdown Converter API",
        "usage": "POST a Google Drive URL to /convert-from-url endpoint",
    }
