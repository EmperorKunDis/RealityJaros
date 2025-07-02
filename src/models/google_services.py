"""
Google Services Integration Models

Database models for Google Workspace integration including:
- Google Sheets automation
- Google Docs document generation  
- Google Drive file management
- Workflow automation tracking
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from src.config.database import Base


class GoogleServiceType(str, Enum):
    """Types of Google Services"""
    SHEETS = "sheets"
    DOCS = "docs"
    DRIVE = "drive"
    GMAIL = "gmail"


class WorkflowTrigger(str, Enum):
    """Workflow trigger types"""
    NEW_EMAIL = "new_email"
    EMAIL_RESPONSE = "email_response"
    CLIENT_ANALYSIS = "client_analysis"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"
    MANUAL = "manual"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoogleServiceCredentials(Base):
    """
    Google Service API credentials and tokens for each user
    """
    __tablename__ = "google_service_credentials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Service configuration
    service_type = Column(String(50), nullable=False)  # GoogleServiceType enum
    is_enabled = Column(Boolean, default=False)
    
    # OAuth credentials
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime, nullable=True)
    
    # Service-specific configuration
    scopes = Column(JSON, nullable=False)  # List of authorized scopes
    service_config = Column(JSON, default={})  # Service-specific settings
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="google_credentials")
    workflows = relationship("GoogleWorkflow", back_populates="credentials")


class GoogleSheetIntegration(Base):
    """
    Google Sheets integration configuration
    """
    __tablename__ = "google_sheet_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Sheet configuration
    spreadsheet_id = Column(String(100), nullable=False)
    spreadsheet_name = Column(String(255), nullable=False)
    sheet_name = Column(String(255), nullable=False)
    
    # Integration settings
    integration_type = Column(String(50), nullable=False)  # "email_log", "client_tracker", "response_metrics"
    is_active = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=True)
    
    # Data mapping configuration
    column_mapping = Column(JSON, default={})  # Maps data fields to sheet columns
    filter_criteria = Column(JSON, default={})  # Criteria for which data to sync
    
    # Sync settings
    sync_frequency = Column(String(20), default="realtime")  # "realtime", "hourly", "daily"
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_row = Column(Integer, default=1)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    sync_logs = relationship("GoogleSheetSyncLog", back_populates="sheet_integration")


class GoogleDocsTemplate(Base):
    """
    Google Docs templates for automated document generation
    """
    __tablename__ = "google_docs_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Template configuration
    template_name = Column(String(255), nullable=False)
    template_type = Column(String(50), nullable=False)  # "email_summary", "client_report", "meeting_notes"
    google_doc_id = Column(String(100), nullable=True)  # Source template doc ID
    
    # Template content
    template_content = Column(Text, nullable=False)  # Template with placeholders
    placeholder_mapping = Column(JSON, default={})  # Maps placeholders to data fields
    
    # Generation settings
    auto_generate = Column(Boolean, default=False)
    output_folder_id = Column(String(100), nullable=True)  # Drive folder for generated docs
    sharing_settings = Column(JSON, default={})  # Default sharing permissions
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    generated_docs = relationship("GoogleGeneratedDoc", back_populates="template")


class GoogleWorkflow(Base):
    """
    Automated workflows using Google Services
    """
    __tablename__ = "google_workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    credentials_id = Column(UUID(as_uuid=True), ForeignKey("google_service_credentials.id"), nullable=False)
    
    # Workflow configuration
    workflow_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # WorkflowTrigger enum
    
    # Trigger conditions
    trigger_conditions = Column(JSON, default={})  # Conditions that must be met
    trigger_schedule = Column(String(100), nullable=True)  # Cron expression for scheduled workflows
    
    # Workflow steps
    workflow_steps = Column(JSON, nullable=False)  # Ordered list of actions
    
    # Settings
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # 1 = highest priority
    max_retries = Column(Integer, default=3)
    timeout_minutes = Column(Integer, default=30)
    
    # Statistics
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    credentials = relationship("GoogleServiceCredentials", back_populates="workflows")
    executions = relationship("GoogleWorkflowExecution", back_populates="workflow")


class GoogleWorkflowExecution(Base):
    """
    Track individual workflow executions
    """
    __tablename__ = "google_workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("google_workflows.id"), nullable=False)
    
    # Execution details
    execution_status = Column(String(20), nullable=False)  # WorkflowStatus enum
    trigger_data = Column(JSON, default={})  # Data that triggered the workflow
    
    # Execution tracking
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Results
    steps_completed = Column(Integer, default=0)
    steps_failed = Column(Integer, default=0)
    output_data = Column(JSON, default={})  # Results from workflow execution
    error_message = Column(Text, nullable=True)
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    workflow = relationship("GoogleWorkflow", back_populates="executions")
    step_logs = relationship("GoogleWorkflowStepLog", back_populates="execution")


class GoogleWorkflowStepLog(Base):
    """
    Detailed logs for individual workflow steps
    """
    __tablename__ = "google_workflow_step_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("google_workflow_executions.id"), nullable=False)
    
    # Step details
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)  # "sheets_update", "docs_create", "drive_upload"
    
    # Execution tracking
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # "pending", "running", "completed", "failed"
    
    # Step data
    input_data = Column(JSON, default={})
    output_data = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    # Service interaction
    service_operation = Column(String(100), nullable=True)  # Specific API operation
    service_request_id = Column(String(100), nullable=True)  # External service request ID
    
    # Relationships
    execution = relationship("GoogleWorkflowExecution", back_populates="step_logs")


class GoogleSheetSyncLog(Base):
    """
    Log entries for Google Sheets synchronization
    """
    __tablename__ = "google_sheet_sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sheet_integration_id = Column(UUID(as_uuid=True), ForeignKey("google_sheet_integrations.id"), nullable=False)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # "manual", "automatic", "scheduled"
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Execution tracking
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Results
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    last_processed_id = Column(String(100), nullable=True)  # Last email/record ID processed
    
    # Metadata
    sync_range = Column(String(50), nullable=True)  # Sheet range that was updated
    api_requests_made = Column(Integer, default=0)
    
    # Relationships
    sheet_integration = relationship("GoogleSheetIntegration", back_populates="sync_logs")


class GoogleGeneratedDoc(Base):
    """
    Track documents generated from templates
    """
    __tablename__ = "google_generated_docs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("google_docs_templates.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Generated document details
    google_doc_id = Column(String(100), nullable=False)
    document_title = Column(String(255), nullable=False)
    document_url = Column(String(500), nullable=False)
    
    # Generation context
    generated_for_type = Column(String(50), nullable=True)  # "email", "client", "report"
    generated_for_id = Column(String(100), nullable=True)  # ID of the related entity
    generation_data = Column(JSON, default={})  # Data used to populate template
    
    # Document settings
    sharing_permissions = Column(JSON, default={})
    folder_id = Column(String(100), nullable=True)
    
    # Metadata
    generated_at = Column(DateTime, default=func.now())
    last_modified_at = Column(DateTime, nullable=True)
    
    # Relationships
    template = relationship("GoogleDocsTemplate", back_populates="generated_docs")
    user = relationship("User")


class GoogleDriveFileMapping(Base):
    """
    Maps application entities to Google Drive files
    """
    __tablename__ = "google_drive_file_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Entity mapping
    entity_type = Column(String(50), nullable=False)  # "email", "client", "response", "report"
    entity_id = Column(String(100), nullable=False)
    
    # Google Drive file details
    drive_file_id = Column(String(100), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # "document", "spreadsheet", "pdf", "attachment"
    file_url = Column(String(500), nullable=False)
    
    # File metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    parent_folder_id = Column(String(100), nullable=True)
    
    # Sync status
    is_synced = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, default=func.now())
    sync_error = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")