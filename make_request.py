import requests
import logging
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url = "https://fastapi-production-fc7c.up.railway.app/convert-from-url"
drive_url = "https://drive.google.com/file/d/10wg3d5JonpROo0krS0XyGf-SWqCIeV5m/preview"

headers = {"access_token": os.getenv("SERVICE_API_KEY")}

try:
    logger.info(f"Sending request to {url} with drive_url: {drive_url}")
    response = requests.post(url, json={"url": drive_url}, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes
    print("Response:", response.json())
    print("Status Code:", response.status_code)
    print("Response Headers:", dict(response.headers))
except requests.exceptions.RequestException as e:
    logger.error(f"Request failed: {str(e)}")
    if hasattr(response, "text"):
        logger.error(f"Response text: {response.text}")
