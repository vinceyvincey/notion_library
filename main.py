from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security.api_key import APIKeyHeader

from app.api.webhook import handle_notion_webhook
from app.core.config import get_settings, setup_logging

settings = get_settings()
setup_logging(settings.debug)

app = FastAPI(title=settings.app_name)

API_KEY_NAME = "access-token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == settings.service_api_key:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


@app.post("/notion-webhook")
async def notion_webhook(request: Request, api_key: str = Depends(get_api_key)):
    """Handle incoming Notion webhook requests."""
    return await handle_notion_webhook(request)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the Notion Library API",
        "version": "2.0",
        "endpoints": {
            "notion-webhook": "POST /notion-webhook",
            "health": "GET /health",
        },
    }
