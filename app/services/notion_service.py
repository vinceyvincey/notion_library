import re

from loguru import logger
from markdown_notion import MarkdownToNotion


class NotionService:
    def __init__(self):
        self.markdown_converter = MarkdownToNotion()

    async def process_drive_url(self, drive_url: str, page_id: str) -> dict:
        """Process a Google Drive URL and convert its content to Notion blocks."""
        try:
            # Extract and validate Google Drive URL
            processed_url = self._process_drive_url(drive_url)
            logger.debug(f"Processed Drive URL: {processed_url}")

            # Convert PDF to markdown using the new package
            markdown_content = await self.markdown_converter.convert_pdf_to_markdown(
                processed_url
            )

            # Create Notion blocks
            result = await self.markdown_converter.create_notion_blocks(
                page_id, markdown_content
            )

            return result

        except Exception as e:
            logger.error(f"Error in process_drive_url: {str(e)}")
            raise

    def _process_drive_url(self, url: str) -> str:
        """Process and validate Google Drive URL."""
        if not url.startswith("https://drive.google.com/uc"):
            file_id_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
            if file_id_match:
                file_id = file_id_match.group(1)
                return f"https://drive.google.com/uc?id={file_id}"
            else:
                raise ValueError(
                    "Could not extract valid Google Drive file ID from URL"
                )
        return url
