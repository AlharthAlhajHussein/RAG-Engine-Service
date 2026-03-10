from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from helpers import settings

# ---------------------------------------------------------
# DOOR 1: ASYNC (For FastAPI)
# ---------------------------------------------------------
ASYNC_DB_URL = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

async_engine = create_async_engine(ASYNC_DB_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ---------------------------------------------------------
# DOOR 2: SYNC (For Celery & db_operations.py)
# ---------------------------------------------------------
# Notice the URL is standard postgresql:// (no asyncpg!)
SYNC_DB_URL = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

sync_engine = create_engine(SYNC_DB_URL, echo=False)

SyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=sync_engine
)