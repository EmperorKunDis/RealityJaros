from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from src.config.database import get_async_session
from src.services.auto_send_service import auto_send_service
from src.api.dependencies import get_current_user
from src.models.user import User
from src.models.response import GeneratedResponse
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

router = APIRouter()


class AutoSendStatusResponse(BaseModel):
    """Response schema for auto-send status"""
    auto_send_enabled: bool
    daily_limit: int
    emails_sent_today: int
    emails_pending: int
    last_processed: str
    confidence_threshold: float


class AutoSendConfigRequest(BaseModel):
    """Request schema for auto-send configuration"""
    auto_respond_enabled: bool
    confidence_threshold: int = 80
    daily_limit: int = 50
    require_confirmation_for_important: bool = True


@router.get("/status", response_model=AutoSendStatusResponse)
async def get_auto_send_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get auto-send status for the authenticated user
    """
    try:
        # Get user's automation configuration
        from src.models.setup_wizard import AutomationConfiguration
        
        stmt = select(AutomationConfiguration).where(
            AutomationConfiguration.user_id == current_user.id
        )
        result = await db.execute(stmt)
        automation_config = result.scalar_one_or_none()
        
        if not automation_config:
            return AutoSendStatusResponse(
                auto_send_enabled=False,
                daily_limit=0,
                emails_sent_today=0,
                emails_pending=0,
                last_processed="never",
                confidence_threshold=0.8
            )
        
        # Count emails sent today
        today = datetime.now().date()
        sent_today_stmt = select(func.count(GeneratedResponse.id)).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status == "sent",
                func.date(GeneratedResponse.sent_at) == today
            )
        )
        sent_today_result = await db.execute(sent_today_stmt)
        emails_sent_today = sent_today_result.scalar() or 0
        
        # Count pending emails
        pending_stmt = select(func.count(GeneratedResponse.id)).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status == "pending_auto_send"
            )
        )
        pending_result = await db.execute(pending_stmt)
        emails_pending = pending_result.scalar() or 0
        
        # Get last processed time
        last_processed_stmt = select(GeneratedResponse.created_at).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status.in_(["sent", "send_failed"])
            )
        ).order_by(GeneratedResponse.created_at.desc()).limit(1)
        
        last_processed_result = await db.execute(last_processed_stmt)
        last_processed_row = last_processed_result.scalar_one_or_none()
        last_processed = last_processed_row.isoformat() if last_processed_row else "never"
        
        return AutoSendStatusResponse(
            auto_send_enabled=automation_config.auto_respond_enabled,
            daily_limit=automation_config.maximum_auto_responses_per_day,
            emails_sent_today=emails_sent_today,
            emails_pending=emails_pending,
            last_processed=last_processed,
            confidence_threshold=automation_config.auto_respond_confidence_threshold / 100.0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auto-send status: {str(e)}"
        )


@router.post("/configure", response_model=Dict[str, Any])
async def configure_auto_send(
    config: AutoSendConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Configure auto-send settings for the authenticated user
    """
    try:
        from src.models.setup_wizard import AutomationConfiguration
        
        # Get or create automation configuration
        stmt = select(AutomationConfiguration).where(
            AutomationConfiguration.user_id == current_user.id
        )
        result = await db.execute(stmt)
        automation_config = result.scalar_one_or_none()
        
        if automation_config:
            # Update existing configuration
            automation_config.auto_respond_enabled = config.auto_respond_enabled
            automation_config.auto_respond_confidence_threshold = config.confidence_threshold
            automation_config.maximum_auto_responses_per_day = config.daily_limit
            automation_config.require_confirmation_for_important = config.require_confirmation_for_important
        else:
            # Create new configuration
            automation_config = AutomationConfiguration(
                user_id=current_user.id,
                auto_respond_enabled=config.auto_respond_enabled,
                auto_respond_confidence_threshold=config.confidence_threshold,
                maximum_auto_responses_per_day=config.daily_limit,
                require_confirmation_for_important=config.require_confirmation_for_important
            )
            db.add(automation_config)
        
        await db.commit()
        
        return {
            "message": "Auto-send configuration updated successfully",
            "configuration": {
                "auto_respond_enabled": automation_config.auto_respond_enabled,
                "confidence_threshold": automation_config.auto_respond_confidence_threshold,
                "daily_limit": automation_config.maximum_auto_responses_per_day,
                "require_confirmation_for_important": automation_config.require_confirmation_for_important
            }
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure auto-send: {str(e)}"
        )


@router.get("/pending", response_model=List[Dict[str, Any]])
async def get_pending_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get emails pending auto-send for the authenticated user
    """
    try:
        stmt = select(GeneratedResponse).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status.in_(["pending_auto_send", "manual_review_required"])
            )
        ).order_by(GeneratedResponse.created_at.desc())
        
        result = await db.execute(stmt)
        pending_responses = result.scalars().all()
        
        pending_list = []
        for response in pending_responses:
            pending_list.append({
                "id": str(response.id),
                "original_email_id": str(response.original_email_id),
                "response_text": response.response_text,
                "confidence_score": response.confidence_score,
                "status": response.status,
                "created_at": response.created_at.isoformat(),
                "review_reason": getattr(response, 'review_reason', None),
                "is_auto_generated": response.is_auto_generated
            })
        
        return pending_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending emails: {str(e)}"
        )


@router.post("/approve/{response_id}", response_model=Dict[str, Any])
async def approve_pending_email(
    response_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually approve a pending email for sending
    """
    try:
        # Get the response
        stmt = select(GeneratedResponse).where(
            and_(
                GeneratedResponse.id == response_id,
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status.in_(["pending_auto_send", "manual_review_required"])
            )
        )
        result = await db.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending email not found"
            )
        
        # Send the email
        send_result = await auto_send_service._send_email_response(response, db)
        
        if send_result["success"]:
            return {
                "message": "Email sent successfully",
                "message_id": send_result.get("message_id"),
                "sent_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {send_result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve email: {str(e)}"
        )


@router.post("/reject/{response_id}", response_model=Dict[str, str])
async def reject_pending_email(
    response_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Reject a pending email (mark as cancelled)
    """
    try:
        # Get the response
        stmt = select(GeneratedResponse).where(
            and_(
                GeneratedResponse.id == response_id,
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status.in_(["pending_auto_send", "manual_review_required"])
            )
        )
        result = await db.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending email not found"
            )
        
        # Mark as rejected
        response.status = "rejected"
        response.rejected_at = datetime.now()
        await db.commit()
        
        return {"message": "Email rejected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject email: {str(e)}"
        )


@router.get("/daily-summary", response_model=Dict[str, Any])
async def get_daily_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Get daily summary for the authenticated user
    """
    try:
        summary = await auto_send_service.generate_daily_summary_email(str(current_user.id))
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily summary: {str(e)}"
        )


@router.post("/send-daily-summary", response_model=Dict[str, Any])
async def send_daily_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger sending of daily summary email
    """
    try:
        success = await auto_send_service.send_daily_summary_email(str(current_user.id))
        
        if success:
            return {
                "message": "Daily summary email sent successfully",
                "sent_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send daily summary email"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send daily summary: {str(e)}"
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_auto_send_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get auto-send analytics for the authenticated user
    """
    try:
        # Get analytics for the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Total responses sent
        total_sent_stmt = select(func.count(GeneratedResponse.id)).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status == "sent",
                GeneratedResponse.created_at >= thirty_days_ago
            )
        )
        total_sent_result = await db.execute(total_sent_stmt)
        total_sent = total_sent_result.scalar() or 0
        
        # Auto vs manual responses
        auto_sent_stmt = select(func.count(GeneratedResponse.id)).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status == "sent",
                GeneratedResponse.is_auto_generated == True,
                GeneratedResponse.created_at >= thirty_days_ago
            )
        )
        auto_sent_result = await db.execute(auto_sent_stmt)
        auto_sent = auto_sent_result.scalar() or 0
        
        # Average confidence score
        avg_confidence_stmt = select(func.avg(GeneratedResponse.confidence_score)).where(
            and_(
                GeneratedResponse.user_id == current_user.id,
                GeneratedResponse.status == "sent",
                GeneratedResponse.created_at >= thirty_days_ago
            )
        )
        avg_confidence_result = await db.execute(avg_confidence_stmt)
        avg_confidence = avg_confidence_result.scalar() or 0.0
        
        return {
            "user_id": str(current_user.id),
            "period": "last_30_days",
            "total_responses_sent": total_sent,
            "auto_responses_sent": auto_sent,
            "manual_responses_sent": total_sent - auto_sent,
            "auto_response_rate": auto_sent / max(total_sent, 1),
            "average_confidence_score": float(avg_confidence),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auto-send analytics: {str(e)}"
        )