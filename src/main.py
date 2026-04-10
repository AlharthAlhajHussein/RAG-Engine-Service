from fastapi import FastAPI
from routers import base, containers, data, search, documents

app = FastAPI(
    title="RAG API",
    description="A Retrieval-Augmented Generation (RAG) API built with FastAPI.",
    version="1.0.0",
    # openapi_url="/openapi.json",
    # docs_url="/docs",
    # redoc_url="/redoc",
    # contact={"name": "Alharth Alhaj Hussein", "email": "alharth.alhaj.hussein@gmail.com"}
)

app.include_router(base.router)
app.include_router(containers.router)
app.include_router(data.router)
app.include_router(documents.router)
app.include_router(search.router)
