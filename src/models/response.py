from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base
import uuid

class WritingStyleProfile(Base):
    """
    Comprehensive writing style analysis profile
    Stores linguistic patterns and communication preferences
    """
    __tablename__ = "writing_style_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Linguistic metrics
    avg_sentence_length = Column(Float, nullable=True)
    avg_paragraph_length = Column(Float, nullable=True)
    vocabulary_complexity = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)
    
    # Style characteristics
    formality_score = Column(Float, nullable=True)
    politeness_score = Column(Float, nullable=True)
    assertiveness_score = Column(Float, nullable=True)
    emotional_tone = Column(String(50), nullable=True)
    
    # Communication patterns
    common_phrases = Column(JSONB, nullable=True)
    signature_patterns = Column(JSONB, nullable=True)
    greeting_patterns = Column(JSONB, nullable=True)
    closing_patterns = Column(JSONB, nullable=True)
    
    # Response behavior
    avg_response_time_hours = Column(Float, nullable=True)
    preferred_response_length = Column(String(50), nullable=True)
    use_bullet_points = Column(Boolean, default=False)
    use_numbered_lists = Column(Boolean, default=False)
    
    # Punctuation and formatting
    exclamation_frequency = Column(Float, nullable=True)
    question_frequency = Column(Float, nullable=True)
    emoji_usage = Column(Boolean, default=False)
    formatting_preferences = Column(JSONB, nullable=True)
    
    # Analysis metadata
    emails_analyzed = Column(Integer, default=0)
    last_analysis = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="writing_style_profile")

class ResponseRule(Base):
    """
    Dynamic response generation rules
    Context-aware templates for automatic responses
    """
    __tablename__ = "response_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    
    # Rule identification
    rule_name = Column(String(255), nullable=False)
    rule_category = Column(String(100), nullable=False)
    
    # Trigger conditions
    trigger_patterns = Column(JSONB, nullable=False)
    trigger_keywords = Column(JSONB, nullable=True)
    subject_patterns = Column(JSONB, nullable=True)
    
    # Response template
    response_template = Column(Text, nullable=False)
    response_variables = Column(JSONB, nullable=True)
    
    # Context requirements
    formality_level = Column(String(50), nullable=True)
    urgency_level = Column(String(50), nullable=True)
    context_requirements = Column(JSONB, nullable=True)
    
    # Rule metadata
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    success_rate = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="response_rules")
    client = relationship("Client", back_populates="response_rules")

class GeneratedResponse(Base):
    """
    AI-generated email responses with quality tracking
    Stores generated drafts and performance metrics
    """
    __tablename__ = "generated_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_email_id = Column(UUID(as_uuid=True), ForeignKey("email_messages.id"), nullable=False)
    
    # Generated content
    generated_response = Column(Text, nullable=False)
    response_type = Column(String(50), nullable=False)  # auto, template, custom
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    style_match_score = Column(Float, nullable=True)
    
    # Generation metadata
    model_used = Column(String(100), nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # RAG context
    retrieved_contexts = Column(JSONB, nullable=True)
    context_sources = Column(JSONB, nullable=True)
    
    # Status tracking
    status = Column(String(50), default="draft")  # draft, reviewed, sent, rejected
    user_feedback = Column(Text, nullable=True)
    was_modified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    original_email = relationship("EmailMessage", back_populates="generated_responses")