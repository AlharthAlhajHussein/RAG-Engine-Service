from fastapi import APIRouter, UploadFile, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import logging
from google.cloud import storage
from celery_tasks.tasks import process_and_embed_document
from models.document import DocumentAsset
from models.connect_database import get_db
from models.db_operations import check_container_exists, check_document_exists, delete_document_and_chunks
from helpers.config import settings
from routers.dependencies import verify_internal_secret

logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/api/v1/documents_upload", 
    tags=["documents_upload"],
    dependencies=[Depends(verify_internal_secret)]
)

@router.post(
    "/{company_id}/{container_id}", 
    status_code=status.HTTP_202_ACCEPTED
)
async def upload_documents_to_container(
    company_id: str, 
    container_id: uuid.UUID, 
    files: List[UploadFile],
    db_session: AsyncSession = Depends(get_db)
):
    """
    Accepts multiple files, streams them to GCP, and triggers the async Celery pipeline.
    """
    
    # --- 1. VERIFY CONTAINER EXISTS ---    
    container = await check_container_exists(db_session, str(container_id), company_id)
    
    if not container:
        raise HTTPException(
            status_code=404, 
            detail=f"Container {container_id} not found or does not belong to {company_id} company."
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
                    
        # 1. The Hierarchical Storage Path
        gcp_blob_path = f"agents_platform_documents/{company_id}/{str(container.id)}/{file.filename}"
        
        try:
            # 2. Stream directly to GCP (Zero RAM Bloat)
            blob = bucket.blob(gcp_blob_path)
            await file.seek(0)
            blob.upload_from_file(file.file, content_type=file.content_type)
            
            
            # 3. Check if a document with the same name already exists in this container
            existing_document = await check_document_exists(db_session, file.filename, str(container.id))
            
            if existing_document:
                # Delete file and it's chunks from DB
                await delete_document_and_chunks(db_session, existing_document)
                    
            # 4. Add the Asset to the database using your ORM
            new_document = DocumentAsset(
                container_id=container.id,
                file_name=file.filename,
                file_type=settings.allowed_types[file.content_type],
                gcp_storage_path=gcp_blob_path,
                status="pending"
            )
            
            db_session.add(new_document)
            await db_session.commit()
            await db_session.refresh(new_document)
            
            # 5. Trigger Celery, passing the newly created Document ID!
            process_and_embed_document.delay(
                document_id=str(new_document.id),
                company_id=company_id,
                container_id=str(container.id),
                gcp_path=gcp_blob_path,
                file_extension=settings.allowed_types[file.content_type]
            )
            
            accepted_files.append({
                "filename": file.filename,
                "status": "queued_for_processing",
                "file_id": str(new_document.id)
            })
            
        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to store document in GCP.")
            
    # Instantly return a 202 Accepted to the user's dashboard!
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED, 
        content={
            "message": f"Successfully queued {len(accepted_files)} files for processing.",
            "container_id": container.name,
            "results": accepted_files
        }
    )