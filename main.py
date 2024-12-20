import logging
import traceback
from fastapi import FastAPI, HTTPException
from markitdown import MarkItDown
import tempfile
import os
import gdown
from pydantic import BaseModel, field_validator
import re
import sys
import requests

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
    try:
        # Create a temporary file to save the downloaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            logger.info(f"Downloading file with ID: {drive_url.url}")
            logger.info(f"Temporary file path: {temp_path}")

            try:
                # Use gdown to download the file using the ID parameter
                logger.info("Attempting download with gdown...")
                output = gdown.download(
                    id=drive_url.url,
                    output=temp_path,
                    quiet=False,
                )

                if not output:
                    logger.error("gdown download failed")
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to download file from Google Drive",
                    )

                logger.info("Download completed using gdown")

                # Verify the file exists and has content
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    logger.error("Downloaded file is empty or does not exist")
                    raise HTTPException(
                        status_code=400,
                        detail="Downloaded file is empty or could not be accessed",
                    )

                file_size = os.path.getsize(temp_path)
                logger.info(f"Downloaded file size: {file_size} bytes")

                # Try to read the first few bytes to verify it's a PDF
                with open(temp_path, "rb") as f:
                    header = f.read(4)
                    if not header.startswith(b"%PDF"):
                        raise HTTPException(
                            status_code=400,
                            detail="The downloaded file is not a valid PDF file",
                        )

                logger.info("File download and validation successful")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error during download with requests: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Failed to download file using requests"
                )

        logger.info("Converting file with MarkItDown")

        try:
            # Convert the file using MarkItDown
            result = md.convert(temp_path)
            if not result or not hasattr(result, "text_content"):
                raise ValueError("Conversion resulted in invalid output")

            logger.info("Conversion successful")
            return {"text_content": result.text_content, "status": "success"}
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Conversion failed")
        finally:
            # Clean up temp file in all cases
            try:
                os.unlink(temp_path)
                logger.info("Temporary file cleaned up")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {str(e)}")

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Google Drive to Markdown Converter API",
        "usage": "POST a Google Drive URL to /convert-from-url endpoint",
    }
