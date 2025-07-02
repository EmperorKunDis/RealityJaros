"""
GDPR Compliance API Routes

Provides REST API endpoints for GDPR compliance functionality including:
- Consent management
- Data subject rights requests
- Privacy settings
- Data export and anonymization
- Audit logging
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from src.api.dependencies import get_current_user, get_database_session
from src.services.gdpr_compliance_service import gdpr_service
from src.models.user import User
from src.models.gdpr_compliance import ConsentStatus, DataCategory, DataProcessingPurpose

router = APIRouter()


# Pydantic schemas for request/response validation

class ConsentRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent being given")
    consent_text: str = Field(..., description="Exact consent text user agreed to")
    legal_basis: str = Field(..., description="Legal basis under GDPR Article 6")
    data_categories: List[str] = Field(..., description="Categories of data consent applies to")
    consent_method: str = Field(..., description="Method of consent collection")
    expires_in_days: Optional[int] = Field(None, description="Optional consent expiration period")


class ConsentWithdrawalRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent to withdraw")


class DataSubjectRequestModel(BaseModel):
    request_type: str = Field(..., description="Type of DSR: access, rectification, erasure, portability")
    request_description: Optional[str] = Field(None, description="Additional details about the request")


class PrivacySettingsUpdate(BaseModel):
    allow_email_analysis: Optional[bool] = None
    allow_style_profiling: Optional[bool] = None
    allow_response_generation: Optional[bool] = None
    allow_data_analytics: Optional[bool] = None
    allow_anonymized_research: Optional[bool] = None
    allow_service_improvement: Optional[bool] = None
    auto_delete_emails_after_days: Optional[int] = None
    auto_delete_responses_after_days: Optional[int] = None
    marketing_emails: Optional[bool] = None
    security_notifications: Optional[bool] = None
    privacy_updates: Optional[bool] = None
    export_format_preference: Optional[str] = None


class AnonymizationRequest(BaseModel):
    anonymization_type: str = Field(default="anonymization", description="anonymization or pseudonymization")
    reason: str = Field(default="data_retention_policy", description="Reason for anonymization")


# Consent Management Endpoints

@router.post("/consent", summary="Record user consent")
async def record_consent(
    consent_request: ConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Record user consent for data processing
    
    This endpoint allows users to provide explicit consent for various
    types of data processing activities in compliance with GDPR Article 7.
    """
    try:
        consent_id = await gdpr_service.record_consent(
            user_id=str(current_user.id),
            consent_type=consent_request.consent_type,
            consent_text=consent_request.consent_text,
            legal_basis=consent_request.legal_basis,
            data_categories=consent_request.data_categories,
            consent_method=consent_request.consent_method,
            request=request,
            expires_in_days=consent_request.expires_in_days
        )
        
        return {
            "success": True,
            "consent_id": consent_id,
            "message": "Consent recorded successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record consent: {str(e)}"
        )


@router.post("/consent/withdraw", summary="Withdraw user consent")
async def withdraw_consent(
    withdrawal_request: ConsentWithdrawalRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Withdraw user consent for data processing
    
    Allows users to withdraw previously given consent as required
    by GDPR Article 7(3).
    """
    try:
        success = await gdpr_service.withdraw_consent(
            user_id=str(current_user.id),
            consent_type=withdrawal_request.consent_type,
            request=request
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="No active consent found for the specified type"
            )
        
        return {
            "success": True,
            "message": "Consent withdrawn successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to withdraw consent: {str(e)}"
        )


@router.get("/consent/{consent_type}/status", summary="Check consent status")
async def check_consent_status(
    consent_type: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if user has valid consent for a specific processing type
    """
    try:
        is_valid = await gdpr_service.check_consent_valid(
            user_id=str(current_user.id),
            consent_type=consent_type
        )
        
        return {
            "consent_type": consent_type,
            "is_valid": is_valid,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check consent status: {str(e)}"
        )


# Data Subject Rights Endpoints

@router.post("/data-subject-request", summary="Submit data subject rights request")
async def submit_data_subject_request(
    dsr_request: DataSubjectRequestModel,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit a data subject rights request under GDPR Articles 15-22
    
    Supports:
    - Right of access (Article 15)
    - Right to rectification (Article 16)
    - Right to erasure (Article 17)
    - Right to data portability (Article 20)
    """
    try:
        request_id = await gdpr_service.handle_data_subject_request(
            user_id=str(current_user.id),
            request_type=dsr_request.request_type,
            request_description=dsr_request.request_description
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "request_type": dsr_request.request_type,
            "status": "pending",
            "due_date": (datetime.utcnow().date() + datetime.timedelta(days=30)).isoformat(),
            "message": "Data subject request submitted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit data subject request: {str(e)}"
        )


@router.get("/export-data", summary="Export user data")
async def export_user_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Export all user data for portability request (GDPR Article 20)
    
    Returns a comprehensive export of all user data in machine-readable format.
    """
    try:
        export_data = await gdpr_service.export_user_data(str(current_user.id))
        
        # Log the data export
        await gdpr_service.log_data_access(
            user_id=str(current_user.id),
            event_type="data_export",
            action="full_data_export_requested",
            resource_type="user_data",
            data_categories=list(DataCategory),
            legal_basis=DataProcessingPurpose.LEGAL_OBLIGATION
        )
        
        return {
            "success": True,
            "export_data": export_data,
            "message": "Data export completed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export user data: {str(e)}"
        )


@router.post("/anonymize-data", summary="Request data anonymization")
async def request_data_anonymization(
    anonymization_request: AnonymizationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Request anonymization or pseudonymization of user data
    
    This can be used for data retention compliance or user requests
    for data anonymization while maintaining service functionality.
    """
    try:
        # Execute anonymization in background
        background_tasks.add_task(
            gdpr_service.anonymize_user_data,
            str(current_user.id),
            anonymization_request.anonymization_type,
            anonymization_request.reason
        )
        
        return {
            "success": True,
            "message": f"Data {anonymization_request.anonymization_type} request submitted",
            "anonymization_type": anonymization_request.anonymization_type,
            "reason": anonymization_request.reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to request data anonymization: {str(e)}"
        )


# Privacy Settings Endpoints

@router.get("/privacy-settings", summary="Get privacy settings")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's privacy settings and data processing preferences
    """
    try:
        settings = await gdpr_service.get_privacy_settings(str(current_user.id))
        
        return {
            "success": True,
            "privacy_settings": settings,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get privacy settings: {str(e)}"
        )


@router.put("/privacy-settings", summary="Update privacy settings")
async def update_privacy_settings(
    settings_update: PrivacySettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user's privacy settings and data processing preferences
    """
    try:
        # Convert to dict, excluding None values
        settings_dict = {k: v for k, v in settings_update.dict().items() if v is not None}
        
        success = await gdpr_service.update_privacy_settings(
            user_id=str(current_user.id),
            settings_update=settings_dict,
            request=request
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update privacy settings"
            )
        
        return {
            "success": True,
            "message": "Privacy settings updated successfully",
            "updated_settings": settings_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update privacy settings: {str(e)}"
        )


# Administrative Endpoints

@router.post("/cleanup-expired-data", summary="Cleanup expired data")
async def cleanup_expired_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger cleanup of expired data according to retention policies
    
    This endpoint is typically called by administrators or scheduled tasks
    to ensure compliance with data retention policies.
    """
    try:
        # Execute cleanup in background
        background_tasks.add_task(gdpr_service.cleanup_expired_data)
        
        return {
            "success": True,
            "message": "Data cleanup task initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate data cleanup: {str(e)}"
        )


@router.get("/audit-summary", summary="Get audit summary")
async def get_audit_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get summary of audit log entries for the user
    
    Provides transparency about data processing activities
    as required by GDPR Article 12.
    """
    try:
        # This would typically query the audit logs for summary information
        # Implementation would include aggregated statistics about data access
        
        return {
            "success": True,
            "user_id": str(current_user.id),
            "period_days": days,
            "message": "Audit summary feature is available",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit summary: {str(e)}"
        )


# Data Categories and Legal Bases Information

@router.get("/data-categories", summary="Get data categories")
async def get_data_categories() -> Dict[str, Any]:
    """
    Get information about data categories used in the system
    
    Helps users understand what types of data are processed.
    """
    return {
        "success": True,
        "data_categories": {
            "basic_identity": "Name, email address, basic profile information",
            "contact_data": "Email content, communication addresses",
            "communication_metadata": "Timestamps, response times, email headers",
            "behavioral_data": "Usage patterns, preferences, interaction history",
            "technical_data": "IP addresses, device information, browser data",
            "profile_data": "Writing style analysis, communication patterns"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/legal-bases", summary="Get legal bases for processing")
async def get_legal_bases() -> Dict[str, Any]:
    """
    Get information about legal bases for data processing under GDPR Article 6
    """
    return {
        "success": True,
        "legal_bases": {
            "consent": "User has given clear consent for processing",
            "contract": "Processing is necessary for contract performance",
            "legal_obligation": "Processing is required by law",
            "vital_interests": "Processing protects vital interests",
            "public_task": "Processing is for public task performance",
            "legitimate_interests": "Processing serves legitimate business interests"
        },
        "timestamp": datetime.utcnow().isoformat()
    }