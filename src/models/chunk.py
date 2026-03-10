import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base


class VectorChunk(Base):
    __tablename__ = "vector_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys linking back to the hierarchy
    container_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_containers.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document_assets.id"), nullable=False, index=True)
    
    # The human-readable text
    chunk_text = Column(String, nullable=False)
    
    # Which order this chunk appeared in the document (useful for LLM context)
    chunk_order = Column(Integer, nullable=False)
    
    # Flexible metadata (e.g., page number, author, headers)
    metadata_ = Column("metadata", JSONB, nullable=True) 
    
    # The mathematical representation of the text (Gemini uses 768 dimensions)
    embedding = Column(Vector(), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    container = relationship("KnowledgeContainer", back_populates="chunks")
    document = relationship("DocumentAsset", back_populates="chunks")
    