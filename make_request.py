import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url = "http://localhost:8000/convert-from-url"
drive_url = (
    "https://drive.google.com/file/d/1kn6H65KevWRbvH58M5Dc-2XpJv8nhJWS/preview"
)

try:
    logger.info(f"Sending request to {url} with drive_url: {drive_url}")
    response = requests.post(url, json={"url": drive_url})
    response.raise_for_status()  # Raise an exception for bad status codes
    print("Response:", response.json())
    print("Status Code:", response.status_code)
    print("Response Headers:", dict(response.headers))
except requests.exceptions.RequestException as e:
    logger.error(f"Request failed: {str(e)}")
    if hasattr(response, "text"):
        logger.error(f"Response text: {response.text}")
