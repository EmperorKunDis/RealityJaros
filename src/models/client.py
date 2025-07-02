from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base
import uuid

class Client(Base):
    """
    Client relationship model with comprehensive profiling
    Tracks communication patterns and business context
    """
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Client identification
    email_address = Column(String(255), nullable=False, index=True)
    email_domain = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255), nullable=True)
    organization_name = Column(String(255), nullable=True)
    
    # Business categorization
    business_category = Column(String(100), nullable=True)
    industry_sector = Column(String(100), nullable=True)
    client_type = Column(String(50), nullable=True)  # prospect, customer, vendor, partner
    
    # Communication analysis
    communication_frequency = Column(String(50), nullable=True)  # daily, weekly, monthly, rare
    avg_response_time_hours = Column(Float, nullable=True)
    formality_level = Column(String(50), nullable=True)  # formal, semi-formal, casual
    preferred_communication_style = Column(String(50), nullable=True)
    
    # Interaction tracking
    total_emails_received = Column(Integer, default=0)
    total_emails_sent = Column(Integer, default=0)
    first_interaction = Column(DateTime(timezone=True), nullable=True)
    last_interaction = Column(DateTime(timezone=True), nullable=True)
    
    # Business intelligence
    common_topics = Column(JSONB, nullable=True)
    frequent_questions = Column(JSONB, nullable=True)
    project_keywords = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Status
    is_active = Column(Boolean, default=True)
    priority_level = Column(String(20), default="normal")  # high, normal, low
    
    # Relationships
    user = relationship("User", back_populates="clients")
    email_messages = relationship("EmailMessage", back_populates="client")
    response_rules = relationship("ResponseRule", back_populates="client")
    
    def __repr__(self):
        return f"<Client(email='{self.email_address}', category='{self.business_category}')>"