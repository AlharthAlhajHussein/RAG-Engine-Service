from fastapi import FastAPI
from routers.base import base_router
from routers.containers import container_router
from routers.data import upload_router

app = FastAPI(
    title="RAG API",
    description="A Retrieval-Augmented Generation (RAG) API built with FastAPI.",
    version="1.0.0",
    # openapi_url="/openapi.json",
    # docs_url="/docs",
    # redoc_url="/redoc",
    # contact={"name": "Alharth Alhaj Hussein", "email": "alharth.alhaj.hussein@gmail.com"}
)

app.include_router(base_router)
app.include_router(container_router)
app.include_router(upload_router)
