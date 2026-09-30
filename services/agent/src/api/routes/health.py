"""Health check endpoint."""

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "env": settings.environment,
        "status": "ok",
    }
