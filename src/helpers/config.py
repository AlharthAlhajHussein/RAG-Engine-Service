from pydantic_settings import BaseSettings
from typing import Optional
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(SRC_DIR, ".env")

class Settings(BaseSettings):
    """Settings for the application."""
    
    app_name: str = "RAG Engine API"
    app_version: str = "1.0.0"
    
    allowed_types: dict[str, str] = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
    }
    
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None
    db_host: Optional[str] = "localhost"
    db_port: Optional[int] = 5432
    
    
    redis_password: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379# Redis settings
    
    
    gemini_api_key: Optional[str] = None
    
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768

    # GCP
    gcp_project_id: str = "agents-platform-490417"
    gcp_storage_bucket: str = "agent-platform-bucket-1"
    
    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        extra = "ignore"
        
        

settings = Settings()