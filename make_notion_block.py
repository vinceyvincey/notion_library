import logging
import os
from typing import Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"  # Current Notion API version


class NotionBlockMaker:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        self.base_url = "https://api.notion.com/v1"

    def create_blocks_from_markdown(self, page_id: str, markdown_content: str) -> bool:
        """
        Convert markdown content to Notion blocks and append them to the specified page.

        Args:
            page_id (str): The ID of the Notion page to append blocks to
            markdown_content (str): The markdown content to convert

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find the start of the actual content (from Abstract)
            content_start = markdown_content.find("**Abstract**")
            if content_start == -1:
                content_start = markdown_content.find("Abstract")

            if content_start == -1:
                logger.error("No Abstract section found in the content")
                return False

            # Only process content from Abstract onwards
            markdown_content = markdown_content[content_start:]

            # Split content into sections based on headers
            sections = self._split_into_sections(markdown_content)

            # Convert sections to Notion blocks
            blocks = []
            for section in sections:
                blocks.extend(self._convert_section_to_blocks(section))

            # Append blocks to the page
            return self._append_blocks_to_page(page_id, blocks)

        except Exception as e:
            logger.error(f"Error creating Notion blocks: {str(e)}")
            return False

    def _split_into_sections(self, markdown_content: str) -> list:
        """Split markdown content into sections based on headers."""
        sections = []
        current_section = []

        for line in markdown_content.split("\n"):
            if line.startswith("**") and "**" in line[2:] and current_section:
                sections.append("\n".join(current_section))
                current_section = []
            current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        return sections

    def _split_long_text(self, text: str, limit: int = 2000) -> list:
        """
        Split text into chunks that respect Notion's character limit.
        Try to split on sentence boundaries when possible.
        """
        if len(text) <= limit:
            return [text]

        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break

            # Try to find a sentence boundary within the limit
            split_point = limit

            # Look for sentence endings (.!?) followed by a space or end of text
            for punct in [". ", "! ", "? "]:
                last_punct = text[:limit].rfind(punct)
                if last_punct != -1:
                    split_point = last_punct + 1  # Include the punctuation
                    break

            # If no sentence boundary found, try splitting on other punctuation
            if split_point == limit:
                for punct in [", ", "; ", "): ", "] "]:
                    last_punct = text[:limit].rfind(punct)
                    if last_punct != -1:
                        split_point = last_punct + 1
                        break

            # If still no good split point, split on space
            if split_point == limit:
                last_space = text[:limit].rfind(" ")
                if last_space != -1:
                    split_point = last_space + 1

            # Add the chunk and continue with remaining text
            chunks.append(text[:split_point].strip())
            text = text[split_point:].strip()

        return chunks

    def _convert_section_to_blocks(self, section: str) -> list:
        """Convert a markdown section to Notion blocks."""
        blocks = []
        lines = section.split("\n")
        was_numbered_list = False  # Track if previous item was a numbered list

        for line in lines:
            if not line.strip():
                continue

            # Handle section headers (e.g., ## Background)
            if line.strip().startswith("##"):
                header_text = line.strip("#").strip()
                blocks.append(self._create_heading_2_block(header_text))
                was_numbered_list = False
            # Handle subsection headers (e.g., ### Methods)
            elif line.strip().startswith("###"):
                header_text = line.strip("#").strip()
                blocks.append(self._create_heading_3_block(header_text))
                was_numbered_list = False
            # Handle bullet points
            elif line.strip().startswith("*"):
                text = line.strip().lstrip("*").strip()
                text = text.replace("**", "")  # Remove bold
                if was_numbered_list:
                    blocks.append(self._create_bullet_list_block(text, indent=1))
                else:
                    blocks.append(self._create_bullet_list_block(text))
            # Handle numbered lists
            elif line.strip().startswith("1.") or line.strip().startswith("2."):
                text = line.strip().split(".", 1)[1].strip()
                text = text.replace("**", "")  # Remove bold
                blocks.append(self._create_numbered_list_block(text))
                was_numbered_list = True
            else:
                # Process text without formatting
                text = line.strip().replace("**", "")  # Remove bold formatting
                paragraph_blocks = self._create_paragraph_block(text)
                if isinstance(paragraph_blocks, list):
                    blocks.extend(paragraph_blocks)
                else:
                    blocks.append(paragraph_blocks)
                was_numbered_list = False

        return blocks

    def _process_inline_formatting(self, text: str) -> list:
        """Process inline markdown formatting."""
        # Split the text by bold markers
        parts = []
        current_pos = 0
        bold_start = text.find("**", current_pos)

        while bold_start != -1:
            # Add non-bold text before
            if bold_start > current_pos:
                parts.append(
                    {"type": "text", "text": {"content": text[current_pos:bold_start]}}
                )

            # Find the end of bold text
            bold_end = text.find("**", bold_start + 2)
            if bold_end == -1:
                break

            # Add bold text
            parts.append(
                {
                    "type": "text",
                    "text": {
                        "content": text[bold_start + 2 : bold_end],
                        "annotations": {"bold": True},
                    },
                }
            )

            current_pos = bold_end + 2
            bold_start = text.find("**", current_pos)

        # Add remaining text
        if current_pos < len(text):
            parts.append({"type": "text", "text": {"content": text[current_pos:]}})

        return parts if parts else [{"type": "text", "text": {"content": text}}]

    def _create_heading_1_block(self, text: str) -> Dict[str, Any]:
        """Create a heading 1 block."""
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": text.strip()}}]
            },
        }

    def _create_heading_2_block(self, text: str) -> Dict[str, Any]:
        """Create a heading 2 block."""
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_heading_3_block(self, text: str) -> Dict[str, Any]:
        """Create a heading 3 block."""
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_bullet_list_block(self, text: str, indent: int = 0) -> Dict[str, Any]:
        """Create a bullet list block."""
        block = {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

        if indent > 0:
            block["bulleted_list_item"]["color"] = "default"
            block["bulleted_list_item"]["children"] = []

        return block

    def _create_numbered_list_block(self, text: str) -> Dict[str, Any]:
        """Create a numbered list block."""
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

    def _create_paragraph_block(self, text: str) -> Dict[str, Any]:
        """Create a paragraph block, splitting if necessary."""
        # Split text if it exceeds Notion's limit
        text_chunks = self._split_long_text(text)

        if len(text_chunks) == 1:
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                },
            }
        else:
            # Return list of paragraph blocks for long text
            return [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    },
                }
                for chunk in text_chunks
            ]

    def _append_blocks_to_page(self, page_id: str, blocks: list) -> bool:
        """Append blocks to a Notion page."""
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"

            # Notion API has a limit of 100 blocks per request
            for i in range(0, len(blocks), 100):
                chunk = blocks[i : i + 100]
                response = requests.patch(
                    url, headers=self.headers, json={"children": chunk}
                )

                if response.status_code != 200:
                    logger.error(f"Failed to append blocks: {response.text}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error appending blocks to page: {str(e)}")
            return False
