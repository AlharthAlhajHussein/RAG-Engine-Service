from sqlalchemy.orm import Session
from models.document import DocumentAsset
from models.chunk import VectorChunk
from models.container import KnowledgeContainer
import logging

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
    