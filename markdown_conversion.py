import logging
import tempfile
import os
import gdown
import requests
import json
import re
from fastapi import HTTPException
from markitdown import MarkItDown
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Configure logging
logger = logging.getLogger(__name__)

md = MarkItDown()


def convert_pdf_to_markdown(drive_url) -> dict:
    """
    Convert a PDF file from Google Drive to Markdown

    Args:
        drive_url: Google Drive URL

    Returns:
        dict: A dictionary with the converted Markdown text and status
    """
    try:
        # Create a temporary file to save the downloaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            logger.info(f"Downloading file with ID: {drive_url}")
            logger.info(f"Temporary file path: {temp_path}")

            try:
                # Extract file ID from URL if necessary
                if drive_url.startswith("https://"):
                    if "id=" in drive_url:
                        file_id = drive_url.split("id=")[1]
                    else:
                        file_id_match = re.search(
                            r"/file/d/([a-zA-Z0-9_-]+)", drive_url
                        )
                        if file_id_match:
                            file_id = file_id_match.group(1)
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail="Could not extract valid Google Drive file ID from URL",
                            )
                else:
                    file_id = drive_url

                # Use gdown to download the file using the ID
                logger.info(f"Attempting download with gdown using file ID: {file_id}")
                output = gdown.download(
                    id=file_id,
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

            # The raw extracted text
            raw_text = result.text_content

            # Now, we use OpenRouter to restructure the text
            prompt_messages = [
                {
                    "role": "user",
                    "content": (
                        "You are a helpful assistant. "
                        "Please take the following extracted text from a PDF and "
                        "reorganize it into clearly defined sections: Abstract, Background, "
                        "Methodology, Results, Discussion, and Conclusion. "
                        "Make sure each section has a clear heading, structure, and is clean, readable text. Methodology should be split into materials (list of materials and sources) and methods (numbered list of steps for each method with clear references to equipment used and parameters if possible\n\n"
                        f"{raw_text}"
                    ),
                }
            ]

            logger.info("Sending request to OpenRouter for cleanup and structuring")

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                },
                data=json.dumps(
                    {
                        "model": "google/gemini-2.0-flash-exp:free",
                        "messages": prompt_messages,
                    }
                ),
            )

            if response.status_code != 200:
                logger.error(
                    f"OpenRouter API returned an error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=500, detail="Failed to process text with OpenRouter"
                )

            json_response = response.json()

            if "choices" not in json_response or len(json_response["choices"]) == 0:
                logger.error("No choices returned from OpenRouter API")
                raise HTTPException(
                    status_code=500, detail="OpenRouter returned no valid choices"
                )

            cleaned_result = json_response["choices"][0]["message"]["content"].strip()
            if not cleaned_result:
                logger.error("Cleaned result from OpenRouter is empty")
                raise HTTPException(
                    status_code=500, detail="OpenRouter returned an empty result"
                )

            logger.info("OpenRouter processing successful")
            return {"text_content": cleaned_result, "status": "success"}
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
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
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
