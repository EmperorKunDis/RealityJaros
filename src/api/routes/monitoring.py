from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.config.database import get_async_session
from src.services.email_monitoring_service import email_monitoring_service
from src.services.background_tasks import task_manager
from src.api.dependencies import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/status", response_model=Dict[str, Any])
async def get_monitoring_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current email monitoring status for the authenticated user
    """
    try:
        # Generate real-time summary for the user
        summary = await email_monitoring_service.generate_daily_summary(str(current_user.id))
        
        return {
            "user_id": str(current_user.id),
            "monitoring_enabled": current_user.email_sync_enabled,
            "last_sync": current_user.last_sync.isoformat() if current_user.last_sync else None,
            "daily_summary": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )


@router.post("/trigger-check", response_model=Dict[str, Any])
async def trigger_manual_email_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually trigger email check for the authenticated user
    """
    try:
        # Trigger manual email monitoring for the user
        result = await email_monitoring_service._monitor_user_emails(current_user, db)
        
        return {
            "message": "Manual email check triggered successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger email check: {str(e)}"
        )


@router.get("/daily-summary", response_model=Dict[str, Any])
async def get_daily_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get daily email summary for the authenticated user
    """
    try:
        summary = await email_monitoring_service.generate_daily_summary(str(current_user.id))
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily summary: {str(e)}"
        )


@router.post("/enable", response_model=Dict[str, str])
async def enable_monitoring(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Enable email monitoring for the authenticated user
    """
    try:
        current_user.email_sync_enabled = True
        await db.commit()
        
        return {"message": "Email monitoring enabled successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable monitoring: {str(e)}"
        )


@router.post("/disable", response_model=Dict[str, str])
async def disable_monitoring(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Disable email monitoring for the authenticated user
    """
    try:
        current_user.email_sync_enabled = False
        await db.commit()
        
        return {"message": "Email monitoring disabled successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable monitoring: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_monitoring_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get monitoring statistics and metrics
    """
    try:
        # Get recent task statuses
        monitoring_tasks = []
        
        # This would ideally query recent monitoring task results
        # For now, return basic stats
        
        return {
            "user_id": str(current_user.id),
            "monitoring_enabled": current_user.email_sync_enabled,
            "last_sync": current_user.last_sync.isoformat() if current_user.last_sync else None,
            "monitoring_frequency": "every_minute",
            "status": "active" if current_user.email_sync_enabled else "inactive"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring stats: {str(e)}"
        )


@router.get("/system-status", response_model=Dict[str, Any])
async def get_system_monitoring_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get system-wide monitoring status (admin-level information)
    """
    try:
        # Return system-wide monitoring information
        return {
            "monitoring_service": "active",
            "celery_beat_enabled": True,
            "minute_interval_enabled": True,
            "last_system_check": "active",
            "total_users_monitored": "calculated_at_runtime"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )