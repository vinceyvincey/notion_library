import logging
from markitdown import MarkItDown
import sys
from dotenv import load_dotenv
import os
import requests
import json

# Load environment variables from .env file
load_dotenv()

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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def convert_pdf_to_markdown(pdf_path):
    logger.info(f"Starting conversion of file: {pdf_path}")

    try:
        # Initialize MarkItDown
        md = MarkItDown()

        # Convert the PDF to markdown
        logger.info("Converting file with MarkItDown")
        result = md.convert(pdf_path)

        if not result or not hasattr(result, "text_content"):
            logger.error("Conversion resulted in invalid output")
            return None

        logger.info("Conversion successful")
        
        # The raw extracted text
        raw_text = result.text_content

        # Now, we use OpenRouter to restructure the text
        # into the specified format:
        # Abstract, Background, Methodology, Results, Discussion, Conclusion

        prompt_messages = [
            {
                "role": "user",
                "content": (
                    "You are a helpful assistant. "
                    "Please take the following extracted text from a PDF and "
                    "reorganize it into clearly defined sections: Abstract, Background, "
                    "Methodology, Results, Discussion, and Conclusion. "
                    "Make sure each section has a clear heading, structure, and is clean, readable text. Methodology shoudl be split into materials (list of materials and sources) and methods (numbered list of steps for each method with clear references to equipment used and parameters if possible\n\n"
                    f"{raw_text}"
                )
            }
        ]

        logger.info("Sending request to OpenRouter for cleanup and structuring")
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": prompt_messages
            })
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API returned an error: {response.status_code} - {response.text}")
            return None

        json_response = response.json()

        if "choices" not in json_response or len(json_response["choices"]) == 0:
            logger.error("No choices returned from OpenRouter API")
            return None

        cleaned_result = json_response["choices"][0]["message"]["content"].strip()
        if not cleaned_result:
            logger.error("Cleaned result from OpenRouter is empty")
            return None

        # Save the cleaned and structured text to a markdown file
        output_path = pdf_path.rsplit(".", 1)[0] + ".md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_result)

        logger.info(f"Structured Markdown saved to: {output_path}")

        return cleaned_result

    except Exception as e:
        logger.error(f"Error during conversion: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    pdf_path = "data/Graphene Materials Mass Production Applications 2017.pdf"
    result = convert_pdf_to_markdown(pdf_path)

    if result:
        print("\nFirst 500 characters of structured text:")
        print(result[:500])
    else:
        print("Conversion failed. Check the logs for details.")