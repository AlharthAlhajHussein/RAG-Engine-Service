from fastapi import APIRouter
from fastapi.responses import JSONResponse
from helpers import settings

base_router = APIRouter(
    prefix="/api/v1",
    tags=["base"],
)

@base_router.get("/")
async def root():
    return JSONResponse(content={"APP NAME": settings.app_name, 
                                 "VERSION": settings.app_version, 
                                 "MESSAGE": "Welcome to the RAG Engine API!"})