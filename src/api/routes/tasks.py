"""
Background Tasks API Routes

This module provides API endpoints for managing background tasks
including email analysis, response generation, and system maintenance.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from src.services.background_tasks import task_manager

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Request/Response Models

class TaskSubmissionRequest(BaseModel):
    """Base task submission request"""
    user_id: str
    priority: Optional[str] = "normal"

class EmailAnalysisRequest(TaskSubmissionRequest):
    """Email analysis task request"""
    email_id: str

class BatchAnalysisRequest(TaskSubmissionRequest):
    """Batch analysis task request"""
    email_ids: List[str]
    max_concurrent: Optional[int] = 5

class ResponseGenerationRequest(TaskSubmissionRequest):
    """Response generation task request"""
    email_id: str
    generation_options: Optional[Dict[str, Any]] = None

class VectorizationRequest(TaskSubmissionRequest):
    """Email vectorization task request"""
    email_ids: List[str]
    update_existing: Optional[bool] = False

class UserProfileUpdateRequest(BaseModel):
    """User profile update task request"""
    user_id: str

class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    traceback: Optional[str] = None
    date_done: Optional[str] = None
    successful: Optional[bool] = None
    error: Optional[str] = None

class TaskSubmissionResponse(BaseModel):
    """Task submission response"""
    task_id: str
    status: str
    submitted_at: str
    estimated_completion: Optional[str] = None

class TaskListResponse(BaseModel):
    """Task list response"""
    tasks: List[TaskStatusResponse]
    total_count: int
    active_count: int
    completed_count: int
    failed_count: int

# Email Analysis Endpoints

@router.post("/analysis/email", response_model=TaskSubmissionResponse)
async def submit_email_analysis(request: EmailAnalysisRequest):
    """
    Submit single email for background analysis
    
    Args:
        request: Email analysis request
        
    Returns:
        Task submission response with task ID
    """
    try:
        logger.info(f"Submitting email {request.email_id} for analysis")
        
        task_id = await task_manager.submit_email_analysis(
            email_id=request.email_id,
            user_id=request.user_id,
            priority=request.priority
        )
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status="submitted",
            submitted_at=datetime.utcnow().isoformat(),
            estimated_completion="2-5 minutes"
        )
        
    except Exception as e:
        logger.error(f"Error submitting email analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit analysis task: {str(e)}")

@router.post("/analysis/batch", response_model=TaskSubmissionResponse)
async def submit_batch_analysis(request: BatchAnalysisRequest):
    """
    Submit batch of emails for background analysis
    
    Args:
        request: Batch analysis request
        
    Returns:
        Task submission response with task ID
    """
    try:
        if len(request.email_ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 emails per batch")
        
        logger.info(f"Submitting {len(request.email_ids)} emails for batch analysis")
        
        task_id = await task_manager.submit_batch_analysis(
            email_ids=request.email_ids,
            user_id=request.user_id
        )
        
        estimated_time = f"{len(request.email_ids) * 2}-{len(request.email_ids) * 5} minutes"
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status="submitted",
            submitted_at=datetime.utcnow().isoformat(),
            estimated_completion=estimated_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting batch analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit batch analysis: {str(e)}")

# Response Generation Endpoints

@router.post("/generation/response", response_model=TaskSubmissionResponse)
async def submit_response_generation(request: ResponseGenerationRequest):
    """
    Submit email for background response generation
    
    Args:
        request: Response generation request
        
    Returns:
        Task submission response with task ID
    """
    try:
        logger.info(f"Submitting email {request.email_id} for response generation")
        
        task_id = await task_manager.submit_response_generation(
            email_id=request.email_id,
            user_id=request.user_id,
            options=request.generation_options
        )
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status="submitted",
            submitted_at=datetime.utcnow().isoformat(),
            estimated_completion="1-3 minutes"
        )
        
    except Exception as e:
        logger.error(f"Error submitting response generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit response generation: {str(e)}")

# Vectorization Endpoints

@router.post("/vectorization/emails", response_model=TaskSubmissionResponse)
async def submit_email_vectorization(request: VectorizationRequest):
    """
    Submit emails for background vectorization
    
    Args:
        request: Vectorization request
        
    Returns:
        Task submission response with task ID
    """
    try:
        if len(request.email_ids) > 200:
            raise HTTPException(status_code=400, detail="Maximum 200 emails per vectorization batch")
        
        logger.info(f"Submitting {len(request.email_ids)} emails for vectorization")
        
        task_id = await task_manager.submit_vectorization(
            email_ids=request.email_ids,
            user_id=request.user_id
        )
        
        estimated_time = f"{len(request.email_ids) // 10 + 1}-{len(request.email_ids) // 5 + 2} minutes"
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status="submitted",
            submitted_at=datetime.utcnow().isoformat(),
            estimated_completion=estimated_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting vectorization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit vectorization: {str(e)}")

# User Profile Endpoints

@router.post("/profile/update", response_model=TaskSubmissionResponse)
async def submit_profile_update(request: UserProfileUpdateRequest):
    """
    Submit user profile update task
    
    Args:
        request: User profile update request
        
    Returns:
        Task submission response with task ID
    """
    try:
        logger.info(f"Submitting profile update for user {request.user_id}")
        
        task_id = await task_manager.submit_user_profile_update(
            user_id=request.user_id
        )
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status="submitted",
            submitted_at=datetime.utcnow().isoformat(),
            estimated_completion="1-2 minutes"
        )
        
    except Exception as e:
        logger.error(f"Error submitting profile update: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit profile update: {str(e)}")

# Task Management Endpoints

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a specific task
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task status information
    """
    try:
        logger.info(f"Getting status for task {task_id}")
        
        status = await task_manager.get_task_status(task_id)
        
        return TaskStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task
    
    Args:
        task_id: Task identifier
        
    Returns:
        Cancellation confirmation
    """
    try:
        logger.info(f"Cancelling task {task_id}")
        
        success = await task_manager.cancel_task(task_id)
        
        if success:
            return {"message": f"Task {task_id} cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel task")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@router.get("/list", response_model=TaskListResponse)
async def list_user_tasks(
    user_id: str = Query(..., description="User identifier"),
    status_filter: Optional[str] = Query(None, regex="^(PENDING|STARTED|SUCCESS|FAILURE|RETRY|REVOKED)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List tasks for a user
    
    Args:
        user_id: User identifier
        status_filter: Filter by task status
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip
        
    Returns:
        List of user tasks
    """
    try:
        logger.info(f"Listing tasks for user {user_id}")
        
        # Note: This is a simplified implementation
        # In a real system, you would query the Celery result backend
        # or maintain a task registry in your database
        
        # For now, return empty list with proper structure
        return TaskListResponse(
            tasks=[],
            total_count=0,
            active_count=0,
            completed_count=0,
            failed_count=0
        )
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

# System Administration Endpoints

@router.post("/admin/cleanup")
async def cleanup_old_tasks():
    """
    Manually trigger cleanup of old completed tasks
    
    Returns:
        Cleanup status
    """
    try:
        logger.info("Triggering manual task cleanup")
        
        # Import the cleanup task
        from src.services.background_tasks import cleanup_old_tasks
        
        # Trigger cleanup task
        task = cleanup_old_tasks.delay()
        
        return {
            "message": "Cleanup task submitted",
            "cleanup_task_id": task.id,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger cleanup: {str(e)}")

@router.post("/admin/analytics")
async def generate_analytics():
    """
    Manually trigger analytics generation
    
    Returns:
        Analytics generation status
    """
    try:
        logger.info("Triggering manual analytics generation")
        
        # Import the analytics task
        from src.services.background_tasks import generate_daily_analytics
        
        # Trigger analytics task
        task = generate_daily_analytics.delay()
        
        return {
            "message": "Analytics generation task submitted",
            "analytics_task_id": task.id,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger analytics: {str(e)}")

@router.get("/admin/workers")
async def get_worker_status():
    """
    Get status of Celery workers
    
    Returns:
        Worker status information
    """
    try:
        logger.info("Getting worker status")
        
        from src.services.background_tasks import celery_app
        
        # Get active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        registered_tasks = inspect.registered()
        
        return {
            "active_workers": active_workers or {},
            "registered_tasks": registered_tasks or {},
            "worker_count": len(active_workers) if active_workers else 0,
            "status": "healthy" if active_workers else "no_workers",
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "worker_count": 0,
            "checked_at": datetime.utcnow().isoformat()
        }

# Health Check Endpoint

@router.get("/health")
async def task_system_health():
    """
    Check health of the background task system
    
    Returns:
        Health status of task system
    """
    try:
        from src.services.background_tasks import celery_app
        
        # Test Celery connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        is_healthy = stats is not None and len(stats) > 0
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "worker_count": len(stats) if stats else 0,
            "broker_connection": "connected" if is_healthy else "disconnected",
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking task system health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "worker_count": 0,
            "broker_connection": "error",
            "checked_at": datetime.utcnow().isoformat()
        }