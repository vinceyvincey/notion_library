import logging
from markitdown import MarkItDown
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_conversion.log"),
    ],
)
logger = logging.getLogger(__name__)


def convert_pdf_to_markdown(pdf_path):
    logger.info(f"Starting conversion of file: {pdf_path}")

    try:
        # Initialize MarkItDown
        md = MarkItDown()

        # Convert the file
        logger.info("Converting file with MarkItDown")
        result = md.convert(pdf_path)

        if not result or not hasattr(result, "text_content"):
            logger.error("Conversion resulted in invalid output")
            return None

        logger.info("Conversion successful")

        # Save the output to a markdown file
        output_path = pdf_path.rsplit(".", 1)[0] + ".md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.text_content)

        logger.info(f"Markdown saved to: {output_path}")
        return result.text_content

    except Exception as e:
        logger.error(f"Error during conversion: {str(e)}")
        logger.error("Full traceback:", exc_info=True)
        return None


if __name__ == "__main__":
    pdf_path = "data/Graphene Materials Mass Production Applications 2017.pdf"
    result = convert_pdf_to_markdown(pdf_path)

    if result:
        print("\nFirst 500 characters of converted text:")
        print(result[:500])
    else:
        print("Conversion failed. Check the logs for details.")
