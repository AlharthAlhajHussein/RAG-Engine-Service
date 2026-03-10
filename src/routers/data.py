from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import uuid
import logging
from google.cloud import storage
from Celery_tasks.tasks import process_and_embed_document
from models.document import DocumentAsset
from models.container import KnowledgeContainer
from models.connect_database import get_db
from helpers.config import settings

logger = logging.getLogger("uvicorn.error")

upload_router = APIRouter(
    prefix="/api/v1/documents", 
    tags=["documents"]
)

@upload_router.post(
    "/upload/{company_id}/{container_id}", 
    status_code=status.HTTP_202_ACCEPTED
)
async def upload_documents_to_container(
    company_id: str, 
    container_id: uuid.UUID, 
    files: List[UploadFile] = File(...),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Accepts multiple files, streams them to GCP, and triggers the async Celery pipeline.
    """
    
    # --- 1. VERIFY CONTAINER EXISTS ---
    stmt = select(KnowledgeContainer).where(
        KnowledgeContainer.id == container_id,
        KnowledgeContainer.company_id == company_id
    )
    result = await db_session.execute(stmt)
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(
            status_code=404, 
            detail="Container not found or does not belong to this company."
        )
    
    # --- 2. PROCEED WITH UPLOAD ---
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.gcp_storage_bucket)
    accepted_files = []
    
    for file in files:
        if file.content_type not in settings.allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.filename}"
            )
            
        safe_filename = file.filename.replace(" ", "_")
        file_uuid = str(uuid.uuid4())
        
        # 1. The Hierarchical Storage Path
        gcp_blob_path = f"agents_platform_documents/{company_id}/{str(container.id)}/{file_uuid}_{safe_filename}"
        
        try:
            # 2. Stream directly to GCP (Zero RAM Bloat)
            blob = bucket.blob(gcp_blob_path)
            await file.seek(0)
            blob.upload_from_file(file.file, content_type=file.content_type)
            
            # 2. Add the Asset to the database using your ORM
            new_document = DocumentAsset(
                container_id=container.id,
                file_name=safe_filename,
                file_type=settings.allowed_types[file.content_type],
                gcp_storage_path=gcp_blob_path,
                status="pending"
            )
            
            db_session.add(new_document)
            await db_session.commit()
            await db_session.refresh(new_document)
            
            # 3. Trigger Celery, passing the newly created Document ID!
            process_and_embed_document.delay(
                document_id=str(new_document.id),
                company_id=company_id,
                container_id=str(container.id),
                gcp_path=gcp_blob_path,
                file_extension=settings.allowed_types[file.content_type]
            )
            
            accepted_files.append({
                "filename": safe_filename,
                "status": "queued_for_processing",
                "file_id": str(new_document.id)
            })
            
        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to store document in GCP.")
            
    # Instantly return a 202 Accepted to the user's dashboard!
    return {
        "message": f"Successfully queued {len(accepted_files)} files for processing.",
        "container_id": container.name,
        "results": accepted_files
    }