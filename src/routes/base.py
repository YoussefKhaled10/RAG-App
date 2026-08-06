from helpers.config import get_settings , Settings
from fastapi import FastAPI , APIRouter , Depends
import os

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

@base_router.get("/welcome")
async def welcome():
    
    settings = get_settings()
    return {"message": f"Welcome to {settings.APP_NAME} version {settings.APP_VERSION}!"}

