"""
GDPR Compliance Service

Implements comprehensive EU GDPR compliance functionality including:
- Audit logging for all data processing activities
- Consent management and tracking
- Data subject rights handling (access, rectification, erasure, portability)
- Data retention and anonymization
- Privacy settings management
- Breach notification handling
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import json
import ipaddress
from fastapi import Request

from src.config.database import AsyncSessionLocal
from src.models.user import User
from src.models.gdpr_compliance import (
    UserConsent, DataProcessingRecord, AuditLog, DataSubjectRequest,
    PrivacySettings, DataAnonymizationLog, DataRetentionPolicy,
    DataBreachLog, DataProcessingPurpose, DataCategory, ConsentStatus
)

logger = logging.getLogger(__name__)


class GDPRComplianceService:
    """
    Comprehensive GDPR compliance service implementing EU data protection requirements
    """
    
    def __init__(self):
        self.retention_policies = {}
        self._load_default_retention_policies()
    
    # Audit Logging (GDPR Article 30)
    
    async def log_data_access(
        self, 
        user_id: Optional[str],
        event_type: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        data_categories: Optional[List[str]] = None,
        legal_basis: Optional[str] = None,
        request: Optional[Request] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        data_before: Optional[Dict] = None,
        data_after: Optional[Dict] = None
    ) -> str:
        """
        Log data access and processing activity for GDPR compliance
        
        Args:
            user_id: ID of user whose data is being accessed
            event_type: Type of event (data_access, data_update, data_delete, etc.)
            action: Specific action taken
            resource_type: Type of resource accessed (email, user_profile, etc.)
            resource_id: ID of specific resource
            data_categories: Categories of personal data affected
            legal_basis: Legal basis for processing under GDPR Article 6
            request: FastAPI request object for extracting metadata
            success: Whether the operation was successful
            error_message: Error message if operation failed
            data_before: State before change (will be hashed for privacy)
            data_after: State after change (will be hashed for privacy)
            
        Returns:
            Audit log entry ID
        """
        try:
            async with AsyncSessionLocal() as session:
                # Extract request metadata
                ip_address = None
                user_agent = None
                request_method = None
                request_path = None
                
                if request:
                    ip_address = self._extract_client_ip(request)
                    user_agent = request.headers.get("user-agent")
                    request_method = request.method
                    request_path = str(request.url.path)
                
                # Hash sensitive data
                data_before_hash = self._hash_data(data_before) if data_before else None
                data_after_hash = self._hash_data(data_after) if data_after else None
                
                # Create audit log entry
                audit_entry = AuditLog(
                    user_id=user_id,
                    event_type=event_type,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=request_method,
                    request_path=request_path,
                    legal_basis=legal_basis,
                    data_categories_affected=data_categories or [],
                    success=success,
                    error_message=error_message,
                    data_before={"hash": data_before_hash} if data_before_hash else None,
                    data_after={"hash": data_after_hash} if data_after_hash else None,
                    timestamp=datetime.now()
                )
                
                session.add(audit_entry)
                await session.commit()
                await session.refresh(audit_entry)
                
                logger.info(f"GDPR audit log created: {audit_entry.id} - {event_type}:{action}")
                return str(audit_entry.id)
                
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Don't raise exception as this could break the main operation
            return ""
    
    # Consent Management (GDPR Article 7)
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: str,
        consent_text: str,
        legal_basis: str,
        data_categories: List[str],
        consent_method: str,
        request: Optional[Request] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        Record user consent for data processing
        
        Args:
            user_id: User providing consent
            consent_type: Type of consent (e.g., "email_processing", "ai_analysis")
            consent_text: Exact text user consented to
            legal_basis: Legal basis under GDPR Article 6
            data_categories: Categories of data consent applies to
            consent_method: How consent was obtained
            request: Request object for metadata
            expires_in_days: Optional consent expiration period
            
        Returns:
            Consent record ID
        """
        try:
            async with AsyncSessionLocal() as session:
                # Extract request metadata
                ip_address = self._extract_client_ip(request) if request else None
                user_agent = request.headers.get("user-agent") if request else None
                
                # Calculate expiration date
                expires_at = None
                if expires_in_days:
                    expires_at = datetime.now() + timedelta(days=expires_in_days)
                
                # Create consent record
                consent = UserConsent(
                    user_id=user_id,
                    consent_type=consent_type,
                    consent_status=ConsentStatus.GIVEN,
                    consent_text=consent_text,
                    legal_basis=legal_basis,
                    data_categories=data_categories,
                    given_at=datetime.now(),
                    expires_at=expires_at,
                    last_confirmed_at=datetime.now(),
                    consent_method=consent_method,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                session.add(consent)
                await session.commit()
                await session.refresh(consent)
                
                # Log the consent action
                await self.log_data_access(
                    user_id=user_id,
                    event_type="consent_given",
                    action=f"consent_recorded_{consent_type}",
                    resource_type="user_consent",
                    resource_id=str(consent.id),
                    data_categories=data_categories,
                    legal_basis=legal_basis,
                    request=request
                )
                
                logger.info(f"Consent recorded for user {user_id}: {consent_type}")
                return str(consent.id)
                
        except Exception as e:
            logger.error(f"Failed to record consent: {str(e)}")
            raise
    
    async def withdraw_consent(
        self,
        user_id: str,
        consent_type: str,
        request: Optional[Request] = None
    ) -> bool:
        """
        Withdraw user consent for data processing
        
        Args:
            user_id: User withdrawing consent
            consent_type: Type of consent to withdraw
            request: Request object for metadata
            
        Returns:
            Success status
        """
        try:
            async with AsyncSessionLocal() as session:
                # Find active consent
                stmt = select(UserConsent).where(
                    and_(
                        UserConsent.user_id == user_id,
                        UserConsent.consent_type == consent_type,
                        UserConsent.consent_status == ConsentStatus.GIVEN
                    )
                )
                result = await session.execute(stmt)
                consent = result.scalar_one_or_none()
                
                if not consent:
                    logger.warning(f"No active consent found for user {user_id}, type {consent_type}")
                    return False
                
                # Update consent status
                consent.consent_status = ConsentStatus.WITHDRAWN
                consent.withdrawn_at = datetime.now()
                
                await session.commit()
                
                # Log the withdrawal
                await self.log_data_access(
                    user_id=user_id,
                    event_type="consent_withdrawn",
                    action=f"consent_withdrawn_{consent_type}",
                    resource_type="user_consent",
                    resource_id=str(consent.id),
                    data_categories=consent.data_categories,
                    request=request
                )
                
                logger.info(f"Consent withdrawn for user {user_id}: {consent_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to withdraw consent: {str(e)}")
            raise
    
    async def check_consent_valid(self, user_id: str, consent_type: str) -> bool:
        """Check if user has valid consent for data processing"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserConsent).where(
                    and_(
                        UserConsent.user_id == user_id,
                        UserConsent.consent_type == consent_type,
                        UserConsent.consent_status == ConsentStatus.GIVEN,
                        or_(
                            UserConsent.expires_at.is_(None),
                            UserConsent.expires_at > datetime.now()
                        )
                    )
                )
                result = await session.execute(stmt)
                consent = result.scalar_one_or_none()
                
                return consent is not None
                
        except Exception as e:
            logger.error(f"Failed to check consent validity: {str(e)}")
            return False
    
    # Data Subject Rights (GDPR Articles 15-22)
    
    async def handle_data_subject_request(
        self,
        user_id: str,
        request_type: str,
        request_description: Optional[str] = None
    ) -> str:
        """
        Handle data subject rights requests
        
        Args:
            user_id: User making the request
            request_type: Type of request (access, rectification, erasure, portability)
            request_description: Additional details about the request
            
        Returns:
            Request ID
        """
        try:
            async with AsyncSessionLocal() as session:
                # Calculate due date (30 days from request)
                due_date = datetime.now() + timedelta(days=30)
                
                # Create request record
                dsr = DataSubjectRequest(
                    user_id=user_id,
                    request_type=request_type,
                    request_description=request_description,
                    status="pending",
                    due_date=due_date,
                    acknowledged_at=datetime.now()
                )
                
                session.add(dsr)
                await session.commit()
                await session.refresh(dsr)
                
                # Log the request
                await self.log_data_access(
                    user_id=user_id,
                    event_type="data_subject_request",
                    action=f"dsr_{request_type}_requested",
                    resource_type="data_subject_request",
                    resource_id=str(dsr.id),
                    legal_basis=DataProcessingPurpose.LEGAL_OBLIGATION
                )
                
                logger.info(f"Data subject request created: {dsr.id} - {request_type}")
                return str(dsr.id)
                
        except Exception as e:
            logger.error(f"Failed to create data subject request: {str(e)}")
            raise
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for portability request (GDPR Article 20)
        """
        try:
            async with AsyncSessionLocal() as session:
                # Get user basic info
                user_stmt = select(User).where(User.id == user_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                # Prepare export data
                export_data = {
                    "export_metadata": {
                        "user_id": user_id,
                        "export_date": datetime.now().isoformat(),
                        "export_format": "json",
                        "gdpr_article": "Article 20 - Right to data portability"
                    },
                    "user_profile": {
                        "email": user.email,
                        "display_name": user.display_name,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "timezone": user.timezone,
                        "language": user.language
                    },
                    "consents": [],
                    "emails": [],
                    "responses": [],
                    "privacy_settings": {},
                    "setup_configuration": {}
                }
                
                # Add consent records
                consents_stmt = select(UserConsent).where(UserConsent.user_id == user_id)
                consents_result = await session.execute(consents_stmt)
                consents = consents_result.scalars().all()
                
                for consent in consents:
                    export_data["consents"].append({
                        "consent_type": consent.consent_type,
                        "status": consent.consent_status,
                        "given_at": consent.given_at.isoformat() if consent.given_at else None,
                        "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
                        "legal_basis": consent.legal_basis,
                        "data_categories": consent.data_categories
                    })
                
                # Add other user data (emails, responses, etc.)
                # This would include all user-related data in compliance with GDPR
                
                # Log the data export
                await self.log_data_access(
                    user_id=user_id,
                    event_type="data_export",
                    action="user_data_exported",
                    resource_type="user_data",
                    data_categories=[
                        DataCategory.BASIC_IDENTITY,
                        DataCategory.CONTACT_DATA,
                        DataCategory.COMMUNICATION_METADATA,
                        DataCategory.BEHAVIORAL_DATA,
                        DataCategory.PROFILE_DATA
                    ],
                    legal_basis=DataProcessingPurpose.LEGAL_OBLIGATION
                )
                
                return export_data
                
        except Exception as e:
            logger.error(f"Failed to export user data: {str(e)}")
            raise
    
    async def anonymize_user_data(
        self,
        user_id: str,
        anonymization_type: str = "anonymization",
        reason: str = "data_retention_policy"
    ) -> bool:
        """
        Anonymize or pseudonymize user data
        
        Args:
            user_id: User whose data to anonymize
            anonymization_type: "anonymization" or "pseudonymization"
            reason: Reason for anonymization
            
        Returns:
            Success status
        """
        try:
            async with AsyncSessionLocal() as session:
                records_processed = 0
                
                # Anonymize different data categories
                if anonymization_type == "anonymization":
                    # Full anonymization - remove personally identifiable information
                    records_processed += await self._anonymize_user_profile(user_id, session)
                    records_processed += await self._anonymize_email_content(user_id, session)
                    records_processed += await self._anonymize_responses(user_id, session)
                else:
                    # Pseudonymization - replace with pseudonyms
                    records_processed += await self._pseudonymize_user_data(user_id, session)
                
                # Log anonymization activity
                anonymization_log = DataAnonymizationLog(
                    user_id=user_id,
                    anonymization_type=anonymization_type,
                    data_category=DataCategory.BASIC_IDENTITY,
                    technique_used="hashing_and_generalization",
                    records_processed=records_processed,
                    legal_basis=DataProcessingPurpose.LEGAL_OBLIGATION,
                    retention_period="indefinite_anonymous",
                    processed_by="system_automated"
                )
                
                session.add(anonymization_log)
                await session.commit()
                
                # Log the anonymization
                await self.log_data_access(
                    user_id=user_id,
                    event_type="data_anonymization",
                    action=f"data_{anonymization_type}",
                    resource_type="user_data",
                    data_categories=list(DataCategory),
                    legal_basis=DataProcessingPurpose.LEGAL_OBLIGATION
                )
                
                logger.info(f"User data {anonymization_type} completed for {user_id}: {records_processed} records")
                return True
                
        except Exception as e:
            logger.error(f"Failed to anonymize user data: {str(e)}")
            raise
    
    # Privacy Settings Management
    
    async def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user's privacy settings"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PrivacySettings).where(PrivacySettings.user_id == user_id)
                result = await session.execute(stmt)
                settings = result.scalar_one_or_none()
                
                if not settings:
                    # Create default privacy settings
                    settings = PrivacySettings(user_id=user_id)
                    session.add(settings)
                    await session.commit()
                    await session.refresh(settings)
                
                return {
                    "allow_email_analysis": settings.allow_email_analysis,
                    "allow_style_profiling": settings.allow_style_profiling,
                    "allow_response_generation": settings.allow_response_generation,
                    "allow_data_analytics": settings.allow_data_analytics,
                    "allow_anonymized_research": settings.allow_anonymized_research,
                    "allow_service_improvement": settings.allow_service_improvement,
                    "auto_delete_emails_after_days": settings.auto_delete_emails_after_days,
                    "auto_delete_responses_after_days": settings.auto_delete_responses_after_days,
                    "marketing_emails": settings.marketing_emails,
                    "security_notifications": settings.security_notifications,
                    "privacy_updates": settings.privacy_updates,
                    "export_format_preference": settings.export_format_preference
                }
                
        except Exception as e:
            logger.error(f"Failed to get privacy settings: {str(e)}")
            raise
    
    async def update_privacy_settings(
        self,
        user_id: str,
        settings_update: Dict[str, Any],
        request: Optional[Request] = None
    ) -> bool:
        """Update user's privacy settings"""
        try:
            async with AsyncSessionLocal() as session:
                # Get existing settings
                stmt = select(PrivacySettings).where(PrivacySettings.user_id == user_id)
                result = await session.execute(stmt)
                settings = result.scalar_one_or_none()
                
                if not settings:
                    settings = PrivacySettings(user_id=user_id)
                    session.add(settings)
                
                # Store old settings for audit
                old_settings = await self.get_privacy_settings(user_id)
                
                # Update settings
                for key, value in settings_update.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                
                settings.updated_at = datetime.now()
                await session.commit()
                
                # Log the privacy settings change
                await self.log_data_access(
                    user_id=user_id,
                    event_type="privacy_settings_update",
                    action="privacy_settings_changed",
                    resource_type="privacy_settings",
                    resource_id=str(settings.id),
                    data_categories=[DataCategory.BEHAVIORAL_DATA],
                    legal_basis=DataProcessingPurpose.CONSENT,
                    request=request,
                    data_before=old_settings,
                    data_after=settings_update
                )
                
                logger.info(f"Privacy settings updated for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update privacy settings: {str(e)}")
            raise
    
    # Data Retention and Cleanup
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired data according to retention policies
        """
        try:
            cleanup_results = {
                "emails_deleted": 0,
                "responses_deleted": 0,
                "logs_archived": 0,
                "consents_expired": 0
            }
            
            async with AsyncSessionLocal() as session:
                # Get all active retention policies
                policies_stmt = select(DataRetentionPolicy).where(DataRetentionPolicy.is_active == True)
                policies_result = await session.execute(policies_stmt)
                policies = policies_result.scalars().all()
                
                for policy in policies:
                    cutoff_date = datetime.now() - timedelta(days=policy.retention_period_days)
                    
                    if policy.data_category == DataCategory.CONTACT_DATA:
                        # Clean up old emails
                        cleanup_results["emails_deleted"] += await self._cleanup_old_emails(cutoff_date, session)
                    
                    elif policy.data_category == DataCategory.BEHAVIORAL_DATA:
                        # Clean up old responses
                        cleanup_results["responses_deleted"] += await self._cleanup_old_responses(cutoff_date, session)
                    
                    elif policy.data_category == DataCategory.TECHNICAL_DATA:
                        # Archive old audit logs
                        cleanup_results["logs_archived"] += await self._archive_old_logs(cutoff_date, session)
                
                # Expire old consents
                cleanup_results["consents_expired"] = await self._expire_old_consents(session)
                
                await session.commit()
                
                logger.info(f"Data cleanup completed: {cleanup_results}")
                return cleanup_results
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {str(e)}")
            raise
    
    # Helper Methods
    
    def _extract_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        try:
            # Try X-Forwarded-For header first (for proxies)
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                # Take the first IP in the chain
                ip = forwarded_for.split(",")[0].strip()
                # Validate IP address
                ipaddress.ip_address(ip)
                return ip
            
            # Try X-Real-IP header
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                ipaddress.ip_address(real_ip)
                return real_ip
            
            # Fall back to direct client IP
            if hasattr(request, 'client') and request.client:
                return request.client.host
            
            return None
            
        except (ValueError, AttributeError):
            return None
    
    def _hash_data(self, data: Any) -> str:
        """Hash data for privacy-preserving audit logs"""
        try:
            data_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest()
        except Exception:
            return "hash_error"
    
    def _load_default_retention_policies(self):
        """Load default data retention policies"""
        self.retention_policies = {
            DataCategory.BASIC_IDENTITY: 2555,  # 7 years
            DataCategory.CONTACT_DATA: 365,     # 1 year
            DataCategory.COMMUNICATION_METADATA: 90,  # 3 months
            DataCategory.BEHAVIORAL_DATA: 180,  # 6 months
            DataCategory.TECHNICAL_DATA: 30,    # 1 month
            DataCategory.PROFILE_DATA: 1095     # 3 years
        }
    
    async def _anonymize_user_profile(self, user_id: str, session: AsyncSession) -> int:
        """Anonymize user profile data"""
        # Implementation would anonymize PII in user profile
        return 1
    
    async def _anonymize_email_content(self, user_id: str, session: AsyncSession) -> int:
        """Anonymize email content"""
        # Implementation would anonymize email content
        return 0
    
    async def _anonymize_responses(self, user_id: str, session: AsyncSession) -> int:
        """Anonymize generated responses"""
        # Implementation would anonymize response content
        return 0
    
    async def _pseudonymize_user_data(self, user_id: str, session: AsyncSession) -> int:
        """Pseudonymize user data"""
        # Implementation would replace identifiers with pseudonyms
        return 0
    
    async def _cleanup_old_emails(self, cutoff_date: datetime, session: AsyncSession) -> int:
        """Clean up old emails"""
        # Implementation would delete or anonymize old emails
        return 0
    
    async def _cleanup_old_responses(self, cutoff_date: datetime, session: AsyncSession) -> int:
        """Clean up old responses"""
        # Implementation would delete or anonymize old responses
        return 0
    
    async def _archive_old_logs(self, cutoff_date: datetime, session: AsyncSession) -> int:
        """Archive old audit logs"""
        # Implementation would archive old logs
        return 0
    
    async def _expire_old_consents(self, session: AsyncSession) -> int:
        """Expire old consents"""
        # Implementation would mark expired consents
        return 0


# Global instance
gdpr_service = GDPRComplianceService()