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

    def _convert_section_to_blocks(self, section: str) -> list:
        """Convert a markdown section to Notion blocks."""
        blocks = []
        lines = section.split("\n")

        for line in lines:
            if not line.strip():
                continue

            # Handle bold headers (e.g., **Abstract**)
            if line.startswith("**") and line.endswith("**"):
                header_text = line.strip("*")
                blocks.append(self._create_heading_1_block(header_text))
            # Handle bullet points
            elif line.strip().startswith("*"):
                text = line.strip().lstrip("*").strip()
                blocks.append(self._create_bullet_list_block(text))
            # Handle numbered lists
            elif line.strip().startswith("1.") or line.strip().startswith("2."):
                text = line.strip().split(".", 1)[1].strip()
                blocks.append(self._create_numbered_list_block(text))
            else:
                # Process inline bold text
                text = self._process_inline_formatting(line)
                blocks.append(self._create_paragraph_block(text))

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

    def _create_bullet_list_block(self, text: str) -> Dict[str, Any]:
        """Create a bullet list block."""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._process_inline_formatting(text.strip())
            },
        }

    def _create_numbered_list_block(self, text: str) -> Dict[str, Any]:
        """Create a numbered list block."""
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": self._process_inline_formatting(text.strip())
            },
        }

    def _create_paragraph_block(self, text: str) -> Dict[str, Any]:
        """Create a paragraph block."""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": self._process_inline_formatting(text.strip())},
        }

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
