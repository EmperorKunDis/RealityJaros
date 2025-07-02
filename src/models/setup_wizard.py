from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.config.database import Base


class SetupWizardProgress(Base):
    """
    Tracks user progress through the 8-step setup wizard
    """
    __tablename__ = "setup_wizard_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Step completion tracking
    step_1_google_auth = Column(Boolean, default=False)
    step_2_email_preferences = Column(Boolean, default=False)
    step_3_writing_style = Column(Boolean, default=False)
    step_4_client_categories = Column(Boolean, default=False)
    step_5_response_automation = Column(Boolean, default=False)
    step_6_notifications = Column(Boolean, default=False)
    step_7_integrations = Column(Boolean, default=False)
    step_8_verification = Column(Boolean, default=False)
    
    # Current step (1-8)
    current_step = Column(Integer, default=1)
    
    # Completion status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="setup_wizard_progress")


class EmailPreferences(Base):
    """
    User email preferences configured during setup wizard
    """
    __tablename__ = "email_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Email checking frequency
    check_frequency_minutes = Column(Integer, default=1)  # Every minute by default
    
    # Email filtering preferences
    filter_marketing = Column(Boolean, default=True)
    filter_spam = Column(Boolean, default=True)
    filter_promotions = Column(Boolean, default=False)
    
    # Response preferences
    auto_respond_enabled = Column(Boolean, default=False)
    auto_respond_delay_minutes = Column(Integer, default=5)
    
    # Languages
    preferred_languages = Column(JSON, default=["cs", "en"])  # Czech and English by default
    
    # Working hours
    working_hours_start = Column(String, default="09:00")
    working_hours_end = Column(String, default="17:00")
    working_days = Column(JSON, default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    
    # Timezone
    timezone = Column(String, default="Europe/Prague")
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="email_preferences")


class WritingStyleConfiguration(Base):
    """
    User writing style configuration from setup wizard
    """
    __tablename__ = "writing_style_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Style preferences
    formality_level = Column(String, default="professional")  # casual, professional, formal
    tone = Column(String, default="friendly")  # friendly, neutral, authoritative
    verbosity = Column(String, default="concise")  # brief, concise, detailed
    
    # Personalization
    signature_style = Column(String, default="standard")  # minimal, standard, detailed
    greeting_style = Column(String, default="contextual")  # minimal, contextual, formal
    
    # Language preferences
    use_technical_terms = Column(Boolean, default=True)
    use_emojis = Column(Boolean, default=False)
    use_abbreviations = Column(Boolean, default=True)
    
    # Response timing
    response_urgency_detection = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="writing_style_configuration")


class ClientCategoryConfiguration(Base):
    """
    User-defined client categories and their preferences
    """
    __tablename__ = "client_category_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Category details
    category_name = Column(String, nullable=False)
    category_description = Column(String)
    
    # Matching rules
    domain_patterns = Column(JSON, default=[])  # List of email domains
    sender_patterns = Column(JSON, default=[])  # List of sender patterns
    subject_keywords = Column(JSON, default=[])  # List of subject keywords
    
    # Response preferences for this category
    response_template = Column(String)
    formality_level = Column(String, default="professional")
    response_delay_minutes = Column(Integer, default=5)
    auto_respond_enabled = Column(Boolean, default=False)
    
    # Priority and routing
    priority_level = Column(String, default="normal")  # low, normal, high, urgent
    escalation_rules = Column(JSON, default=[])
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="client_category_configurations")


class AutomationConfiguration(Base):
    """
    Automation settings configured during setup wizard
    """
    __tablename__ = "automation_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Email automation
    auto_respond_enabled = Column(Boolean, default=False)
    auto_respond_confidence_threshold = Column(Integer, default=80)  # 0-100
    
    # Daily summaries
    daily_summary_enabled = Column(Boolean, default=True)
    daily_summary_time = Column(String, default="08:00")
    
    # Weekly reports
    weekly_report_enabled = Column(Boolean, default=True)
    weekly_report_day = Column(String, default="monday")
    weekly_report_time = Column(String, default="09:00")
    
    # Integration automation
    google_sheets_integration = Column(Boolean, default=False)
    google_docs_integration = Column(Boolean, default=False)
    google_drive_integration = Column(Boolean, default=False)
    
    # Safety settings
    maximum_auto_responses_per_day = Column(Integer, default=50)
    require_confirmation_for_important = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="automation_configuration")


class NotificationConfiguration(Base):
    """
    Notification preferences configured during setup wizard
    """
    __tablename__ = "notification_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Email notifications
    email_notifications_enabled = Column(Boolean, default=True)
    notification_email = Column(String)  # Can be different from primary email
    
    # Notification types
    notify_new_emails = Column(Boolean, default=False)
    notify_auto_responses = Column(Boolean, default=True)
    notify_high_priority = Column(Boolean, default=True)
    notify_errors = Column(Boolean, default=True)
    
    # Frequency controls
    digest_frequency = Column(String, default="daily")  # realtime, hourly, daily, weekly
    quiet_hours_start = Column(String, default="22:00")
    quiet_hours_end = Column(String, default="07:00")
    
    # Channels
    browser_notifications = Column(Boolean, default=True)
    mobile_notifications = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_configuration")


class IntegrationConfiguration(Base):
    """
    Third-party integration settings
    """
    __tablename__ = "integration_configuration"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Google Workspace integrations
    gmail_integration = Column(Boolean, default=True)
    google_calendar_integration = Column(Boolean, default=False)
    google_drive_integration = Column(Boolean, default=False)
    google_sheets_integration = Column(Boolean, default=False)
    google_docs_integration = Column(Boolean, default=False)
    
    # AI Model preferences
    preferred_ai_model = Column(String, default="openai")  # openai, local, hybrid
    local_model_path = Column(String)
    
    # Vector database preferences
    vector_db_type = Column(String, default="chromadb")  # chromadb, faiss, weaviate
    
    # External services
    slack_integration = Column(Boolean, default=False)
    teams_integration = Column(Boolean, default=False)
    
    # Configuration data
    integration_settings = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="integration_configuration")