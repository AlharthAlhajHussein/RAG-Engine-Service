from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from models.connect_database import get_db
from models.db_operations import check_container_exists, check_document_exists_by_id, delete_document_and_chunks
from routers.dependencies import verify_internal_secret

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Depends(verify_internal_secret)]
)

@router.delete("/{company_id}/{container_id}/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    company_id: str,
    container_id: uuid.UUID,
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    # 1. Verify container and document validity
    container = await check_container_exists(db, str(container_id), company_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found.")
        
    document = await check_document_exists_by_id(db, document_id, str(container_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 2. Delete safely
    await delete_document_and_chunks(db_session=db, document=document)
    return None