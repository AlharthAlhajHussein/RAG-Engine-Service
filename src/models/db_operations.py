from sqlalchemy.orm import Session
from models.document import DocumentAsset
from models.chunk import VectorChunk
from models.container import KnowledgeContainer
import logging
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")

def update_document_status(db_session: Session, document_id: str, new_status: str):
    """Updates the status of a document ('processing', 'completed', 'failed')."""
    document = db_session.query(DocumentAsset).filter(DocumentAsset.id == document_id).first()
    if document:
        document.status = new_status
        db_session.commit()
    else:
        logger.error(f"Document {document_id} not found to update status to {new_status}")

def save_vector_chunks(db_session: Session, chunks_data: list[dict]):
    """
    Takes a list of dictionaries and efficiently bulk-inserts them into the VectorChunk table.
    """
    try:
        # Convert dictionaries to SQLAlchemy Model instances
        db_chunks = [VectorChunk(**data) for data in chunks_data]
        
        # bulk_save_objects is highly optimized for inserting hundreds of rows at once
        db_session.bulk_save_objects(db_chunks)
        db_session.commit()
        return len(db_chunks)
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to insert vector chunks: {e}")
        raise e
    
async def check_container_exists(db_session: AsyncSession, container_id: str, company_id: str):
    stmt = select(KnowledgeContainer).filter(
        KnowledgeContainer.id == container_id,
        KnowledgeContainer.company_id == company_id
    )
    result = await db_session.execute(stmt)
    # .scalars().first() extracts the actual model instance from the result
    return result.scalars().first()

async def check_document_exists(db_session: AsyncSession, file_name: str, container_id: str):
    stmt = select(DocumentAsset).filter(
        DocumentAsset.file_name == file_name,
        DocumentAsset.container_id == container_id
    )
    result = await db_session.execute(stmt)
    return result.scalars().first()

async def delete_document_and_chunks(db_session: AsyncSession, document_id: str) -> bool:
    try:
        # 1. Delete the chunks
        stmt_chunks = delete(VectorChunk).filter(VectorChunk.document_id == document_id)
        await db_session.execute(stmt_chunks)
        
        # 2. Delete the document
        stmt_doc = delete(DocumentAsset).filter(DocumentAsset.id == document_id)
        await db_session.execute(stmt_doc)
        
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        logger.error(f"Failed to delete document {document_id} and its chunks: {e}")
        raise e
    
    return True

async def semantic_search(db_session: AsyncSession, container_id: str, query_vector: str, top_k: int):
    
    # --- 2. VECTOR SEARCH USING PGVECTOR ---
    try:
        # Calculate Cosine Distance
        # pgvector uses `<=>` under the hood for cosine distance. 
        # Similarity is mathematically: 1.0 - Cosine Distance
        distance_expr = VectorChunk.embedding.cosine_distance(query_vector)
        similarity_expr = (1.0 - distance_expr).label("similarity_score")
        
        # Build the heavily optimized query
        search_stmt = (
            select(VectorChunk, similarity_expr)
            .where(VectorChunk.container_id == container_id)
            .order_by(distance_expr) # Order by closest distance (fastest via HNSW)
            .limit(top_k)
        )
        
        search_results = await db_session.execute(search_stmt)
        
        return search_results
        
    except Exception as e:
        logger.error(f"Database search failed: {e}")
        raise HTTPException(status_code=500, detail="Vector database search failed.")
    

    