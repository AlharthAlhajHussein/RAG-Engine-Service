import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base

class VectorChunk(Base):
    __tablename__ = "vector_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    container_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_containers.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document_assets.id"), nullable=False, index=True)
    
    chunk_text = Column(String, nullable=False)
    chunk_order = Column(Integer, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True) 
    
    # Best Practice: Explicitly define the Gemini dimension size (768)
    embedding = Column(Vector(768), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    container = relationship("KnowledgeContainer", back_populates="chunks")
    document = relationship("DocumentAsset", back_populates="chunks")

    # --- ADD THIS BLOCK FOR HNSW INDEXING ---
    __table_args__ = (
        Index(
            'ix_vector_chunks_embedding_hnsw',  # Name of the index
            'embedding',                        # Column to index
            postgresql_using='hnsw',            # The state-of-the-art algorithm
            postgresql_with={'m': 16, 'ef_construction': 64}, # Tuning parameters
            postgresql_ops={'embedding': 'vector_cosine_ops'} # The distance metric
        ),
    )