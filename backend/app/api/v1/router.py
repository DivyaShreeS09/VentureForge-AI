from fastapi import APIRouter

from app.api.v1 import analyses, health, models_status, startups, system_status
from app.core.config import settings

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(health.router)
api_router.include_router(startups.router)
api_router.include_router(analyses.router)
api_router.include_router(models_status.router)
api_router.include_router(system_status.router)
