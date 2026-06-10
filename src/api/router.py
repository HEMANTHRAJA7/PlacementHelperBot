from fastapi import APIRouter
from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.webhook import router as webhook_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(webhook_router)


