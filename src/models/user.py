from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base
import uuid

class User(Base):
    """
    User model with comprehensive profile management
    Stores authentication data and user preferences
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_id = Column(String(255), unique=True, nullable=True)
    display_name = Column(String(255), nullable=True)
    profile_picture = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Settings
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="cs")
    email_sync_enabled = Column(Boolean, default=True)
    auto_response_enabled = Column(Boolean, default=False)
    
    # Relationships
    clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")
    email_messages = relationship("EmailMessage", back_populates="user", cascade="all, delete-orphan")
    writing_style_profile = relationship("WritingStyleProfile", back_populates="user", uselist=False)
    response_rules = relationship("ResponseRule", back_populates="user", cascade="all, delete-orphan")
    
    # Setup wizard relationships
    setup_wizard_progress = relationship("SetupWizardProgress", back_populates="user", uselist=False)
    email_preferences = relationship("EmailPreferences", back_populates="user", uselist=False)
    writing_style_configuration = relationship("WritingStyleConfiguration", back_populates="user", uselist=False)
    client_category_configurations = relationship("ClientCategoryConfiguration", back_populates="user", cascade="all, delete-orphan")
    automation_configuration = relationship("AutomationConfiguration", back_populates="user", uselist=False)
    notification_configuration = relationship("NotificationConfiguration", back_populates="user", uselist=False)
    integration_configuration = relationship("IntegrationConfiguration", back_populates="user", uselist=False)
    
    # GDPR compliance relationships
    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
    processing_records = relationship("DataProcessingRecord", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    data_subject_requests = relationship("DataSubjectRequest", back_populates="user", cascade="all, delete-orphan")
    privacy_settings = relationship("PrivacySettings", back_populates="user", uselist=False)
    anonymization_logs = relationship("DataAnonymizationLog", back_populates="user", cascade="all, delete-orphan")
    
    # Google Services integration relationships
    google_credentials = relationship("GoogleServiceCredentials", back_populates="user", cascade="all, delete-orphan")
    google_sheet_integrations = relationship("GoogleSheetIntegration", cascade="all, delete-orphan")
    google_docs_templates = relationship("GoogleDocsTemplate", cascade="all, delete-orphan")
    google_workflows = relationship("GoogleWorkflow", cascade="all, delete-orphan")
    google_generated_docs = relationship("GoogleGeneratedDoc", cascade="all, delete-orphan")
    google_drive_mappings = relationship("GoogleDriveFileMapping", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(email='{self.email}', is_active={self.is_active})>"