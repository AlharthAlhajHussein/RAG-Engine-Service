import uuid
from sqlalchemy import Column, String, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class KnowledgeContainer(Base):
    __tablename__ = "knowledge_containers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    documents = relationship("DocumentAsset", back_populates="container", cascade="all, delete-orphan")
    chunks = relationship("VectorChunk", back_populates="container", cascade="all, delete-orphan")

    # --- ADD THIS BLOCK ---
    # This tells PostgreSQL: The combination of company_id + name MUST be unique.
    __table_args__ = (
        UniqueConstraint('company_id', 'name', name='uix_company_container_name'),
    )