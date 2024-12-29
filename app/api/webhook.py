from fastapi import HTTPException, Request
from loguru import logger

from app.core.config import get_settings
from app.services.notion_service import NotionService

settings = get_settings()


async def handle_notion_webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"Received Notion webhook payload: {payload}")

        page_id = payload.get("data", {}).get("id")
        if not page_id:
            raise HTTPException(
                status_code=400, detail="No page ID found in the request"
            )

        logger.debug(f"Processing page ID: {page_id}")

        files = (
            payload.get("data", {})
            .get("properties", {})
            .get("File", {})
            .get("files", [])
        )

        if not files:
            raise HTTPException(status_code=400, detail="No files found in the request")

        file_info = files[0]
        drive_url = file_info.get("external", {}).get("url", "").strip(";")

        if not drive_url:
            raise HTTPException(
                status_code=400, detail="No valid URL found in the file information"
            )

        logger.debug(f"Processing Google Drive URL: {drive_url}")

        notion_service = NotionService()
        result = await notion_service.process_drive_url(drive_url, page_id)

        return {
            "status": "success",
            "message": "Content added to Notion page",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error processing Notion webhook: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to process Notion webhook")
