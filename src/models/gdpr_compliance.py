"""
GDPR Compliance Models

Implements data models for EU GDPR compliance including audit logging,
data protection tracking, consent management, and data processing records.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from src.config.database import Base


class DataProcessingPurpose(str, Enum):
    """GDPR Article 6 lawful bases for processing"""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategory(str, Enum):
    """Categories of personal data under GDPR"""
    BASIC_IDENTITY = "basic_identity"  # Name, email
    CONTACT_DATA = "contact_data"  # Email content, addresses
    COMMUNICATION_METADATA = "communication_metadata"  # Timestamps, response times
    BEHAVIORAL_DATA = "behavioral_data"  # Usage patterns, preferences
    TECHNICAL_DATA = "technical_data"  # IP addresses, device info
    PROFILE_DATA = "profile_data"  # Writing style, communication patterns


class ConsentStatus(str, Enum):
    """Consent status for GDPR compliance"""
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class DataRetentionPolicy(Base):
    """
    Data retention policies for different types of data
    GDPR Article 5(1)(e) - storage limitation
    """
    __tablename__ = "data_retention_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_category = Column(String(50), nullable=False)  # DataCategory enum
    retention_period_days = Column(Integer, nullable=False)
    legal_basis = Column(String(50), nullable=False)  # DataProcessingPurpose enum
    description = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class UserConsent(Base):
    """
    User consent tracking for GDPR Article 7
    """
    __tablename__ = "user_consent"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Consent details
    consent_type = Column(String(100), nullable=False)  # e.g., "email_processing", "ai_analysis"
    consent_status = Column(String(20), nullable=False)  # ConsentStatus enum
    consent_text = Column(Text, nullable=False)  # Exact text user consented to
    
    # Legal basis
    legal_basis = Column(String(50), nullable=False)  # DataProcessingPurpose enum
    data_categories = Column(JSON, nullable=False)  # List of DataCategory enums
    
    # Timestamps
    given_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_confirmed_at = Column(DateTime, nullable=True)
    
    # Audit trail
    consent_method = Column(String(50))  # "setup_wizard", "api", "web_interface"
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="consents")


class DataProcessingRecord(Base):
    """
    Record of processing activities under GDPR Article 30
    """
    __tablename__ = "data_processing_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Processing details
    processing_activity = Column(String(100), nullable=False)  # "email_analysis", "response_generation"
    purpose = Column(String(100), nullable=False)
    legal_basis = Column(String(50), nullable=False)  # DataProcessingPurpose enum
    data_categories = Column(JSON, nullable=False)  # List of DataCategory enums
    
    # Data subjects and recipients
    data_subject_categories = Column(JSON)  # e.g., ["customers", "employees"]
    recipient_categories = Column(JSON)  # Who receives the data
    
    # International transfers
    third_country_transfers = Column(JSON)  # Countries data is transferred to
    transfer_safeguards = Column(Text)  # Safeguards for international transfers
    
    # Retention
    retention_period = Column(String(100))
    deletion_criteria = Column(Text)
    
    # Processing timestamps
    processed_at = Column(DateTime, default=func.now())
    data_source = Column(String(100))  # Where data came from
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="processing_records")


class AuditLog(Base):
    """
    Comprehensive audit log for GDPR compliance
    Records all data access and processing activities
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # "data_access", "data_update", "data_delete"
    action = Column(String(100), nullable=False)  # Specific action taken
    resource_type = Column(String(50), nullable=False)  # "email", "user_profile", "response"
    resource_id = Column(String(100), nullable=True)  # ID of affected resource
    
    # Request details
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_method = Column(String(10))  # GET, POST, PUT, DELETE
    request_path = Column(String(500))
    
    # Processing details
    legal_basis = Column(String(50))  # Legal basis for processing
    data_categories_affected = Column(JSON)  # Categories of data affected
    
    # Results
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Data details
    data_before = Column(JSON, nullable=True)  # State before change (hashed/anonymized)
    data_after = Column(JSON, nullable=True)  # State after change (hashed/anonymized)
    
    # Metadata
    timestamp = Column(DateTime, default=func.now())
    session_id = Column(String(100))
    correlation_id = Column(String(100))  # For tracking related events
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")


class DataSubjectRequest(Base):
    """
    GDPR Data Subject Rights requests (Articles 15-22)
    """
    __tablename__ = "data_subject_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Request details
    request_type = Column(String(50), nullable=False)  # "access", "rectification", "erasure", "portability"
    request_description = Column(Text)
    
    # Status tracking
    status = Column(String(50), default="pending")  # "pending", "in_progress", "completed", "rejected"
    priority = Column(String(20), default="normal")  # "low", "normal", "high", "urgent"
    
    # Legal requirements
    identity_verified = Column(Boolean, default=False)
    verification_method = Column(String(100))
    verification_date = Column(DateTime)
    
    # Processing timeline
    requested_at = Column(DateTime, default=func.now())
    acknowledged_at = Column(DateTime)
    due_date = Column(DateTime)  # Must respond within 30 days (GDPR Article 12)
    completed_at = Column(DateTime)
    
    # Response details
    response_method = Column(String(50))  # "email", "secure_download", "api"
    response_data = Column(JSON)  # Metadata about provided data
    rejection_reason = Column(Text)
    
    # Audit trail
    assigned_to = Column(String(100))  # Staff member handling request
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="data_subject_requests")


class DataBreachLog(Base):
    """
    Data breach notification log (GDPR Article 33-34)
    """
    __tablename__ = "data_breach_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Breach details
    breach_type = Column(String(50), nullable=False)  # "confidentiality", "integrity", "availability"
    severity_level = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    description = Column(Text, nullable=False)
    
    # Affected data
    affected_users_count = Column(Integer, default=0)
    data_categories_affected = Column(JSON, nullable=False)
    likely_consequences = Column(Text)
    
    # Timeline
    occurred_at = Column(DateTime, nullable=False)
    discovered_at = Column(DateTime, default=func.now())
    contained_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Notifications
    authority_notified = Column(Boolean, default=False)
    authority_notified_at = Column(DateTime)
    users_notified = Column(Boolean, default=False)
    users_notified_at = Column(DateTime)
    
    # Response measures
    measures_taken = Column(Text)
    preventive_measures = Column(Text)
    
    # Metadata
    reported_by = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class PrivacySettings(Base):
    """
    User privacy settings and preferences
    """
    __tablename__ = "privacy_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Data processing preferences
    allow_email_analysis = Column(Boolean, default=True)
    allow_style_profiling = Column(Boolean, default=True)
    allow_response_generation = Column(Boolean, default=True)
    allow_data_analytics = Column(Boolean, default=False)
    
    # Sharing preferences
    allow_anonymized_research = Column(Boolean, default=False)
    allow_service_improvement = Column(Boolean, default=True)
    
    # Retention preferences
    auto_delete_emails_after_days = Column(Integer)  # User-defined retention period
    auto_delete_responses_after_days = Column(Integer)
    
    # Communication preferences
    marketing_emails = Column(Boolean, default=False)
    security_notifications = Column(Boolean, default=True)
    privacy_updates = Column(Boolean, default=True)
    
    # Data export preferences
    export_format_preference = Column(String(20), default="json")  # "json", "csv", "xml"
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="privacy_settings")


class DataAnonymizationLog(Base):
    """
    Log of data anonymization and pseudonymization activities
    """
    __tablename__ = "data_anonymization_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Anonymization details
    anonymization_type = Column(String(50), nullable=False)  # "anonymization", "pseudonymization"
    data_category = Column(String(50), nullable=False)
    technique_used = Column(String(100))  # "hashing", "encryption", "generalization"
    
    # Processing details
    records_processed = Column(Integer, default=0)
    original_data_hash = Column(String(256))  # Hash of original data for verification
    anonymized_data_hash = Column(String(256))  # Hash of anonymized data
    
    # Legal compliance
    legal_basis = Column(String(50))
    retention_period = Column(String(100))
    
    # Metadata
    processed_at = Column(DateTime, default=func.now())
    processed_by = Column(String(100))  # System or user who triggered anonymization
    
    # Relationships
    user = relationship("User", back_populates="anonymization_logs")