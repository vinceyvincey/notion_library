import gdown
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("download_test.log"),
    ],
)
logger = logging.getLogger(__name__)


def download_from_drive(url: str, output_dir: str = "data"):
    """
    Download a file from Google Drive and save it to the data directory.

    Args:
        url: Google Drive sharing URL
        output_dir: Directory to save the file (default: "data")
    """
    logger.info(f"Starting download from URL: {url}")

    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Convert preview URL to download URL
        url = url.replace("/preview", "/view")

        # Set output path
        output_path = (
            Path(output_dir)
            / "Graphene Materials Mass Production Applications 2017.pdf"
        )

        # Download using gdown with URL
        logger.info(f"Downloading to: {output_path}")
        output = gdown.download(
            url=url, output=str(output_path), quiet=False, fuzzy=True
        )

        if output:
            logger.info(f"Successfully downloaded file to: {output_path}")
            return True
        else:
            logger.error("Download failed")
            return False

    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        logger.error("Full traceback:", exc_info=True)
        return False


if __name__ == "__main__":
    # Google Drive sharing URL
    drive_url = (
        "https://drive.google.com/file/d/1kn6H65KevWRbvH58M5Dc-2XpJv8nhJWS/preview"
    )

    if download_from_drive(drive_url):
        print("\nDownload successful!")
    else:
        print("\nDownload failed. Check the logs for details.")
