import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class DocumentAsset(Base):
    __tablename__ = "document_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    container_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_containers.id"), nullable=False, index=True)
    
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # e.g., 'pdf', 'docx'
    gcp_storage_path = Column(String(500), nullable=False)
    
    # Status tracks the Celery worker: 'pending', 'processing', 'completed', 'failed'
    status = Column(String(50), default="pending", nullable=False) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    container = relationship("KnowledgeContainer", back_populates="documents")
    chunks = relationship("VectorChunk", back_populates="document", cascade="all, delete-orphan")
    