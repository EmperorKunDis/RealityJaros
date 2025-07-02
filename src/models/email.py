from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base
import uuid

class EmailMessage(Base):
    """
    Comprehensive email message model with metadata
    Stores complete email data for analysis and RAG
    """
    __tablename__ = "email_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    
    # Gmail API identifiers
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    
    # Email metadata
    direction = Column(String(20), nullable=False)  # incoming, outgoing
    subject = Column(Text, nullable=True)
    sender = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    cc_recipients = Column(JSONB, nullable=True)
    bcc_recipients = Column(JSONB, nullable=True)
    
    # Email content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    
    # Gmail metadata
    labels = Column(JSONB, nullable=True)
    importance = Column(String(20), nullable=True)
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    
    # Timestamps
    sent_datetime = Column(DateTime(timezone=True), nullable=False)
    received_datetime = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    is_chunked = Column(Boolean, default=False)
    is_embedded = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Analysis results
    sentiment_score = Column(Float, nullable=True)
    urgency_level = Column(String(20), nullable=True)
    topic_categories = Column(JSONB, nullable=True)
    extracted_entities = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="email_messages")
    client = relationship("Client", back_populates="email_messages")
    generated_responses = relationship("GeneratedResponse", back_populates="original_email")
    
    def __repr__(self):
        return f"<EmailMessage(subject='{self.subject[:50] if self.subject else 'No subject'}...', direction='{self.direction}')>"

class EmailChunk(Base):
    """
    Text chunks of emails for vector database storage
    Optimized for RAG retrieval operations
    """
    __tablename__ = "email_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_message_id = Column(UUID(as_uuid=True), ForeignKey("email_messages.id"), nullable=False)
    
    # Chunk data
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), nullable=False)  # subject, body, signature
    
    # Vector database references
    vector_collection = Column(String(100), nullable=True)
    vector_id = Column(String(255), nullable=True)
    
    # Metadata
    token_count = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    email_message = relationship("EmailMessage")