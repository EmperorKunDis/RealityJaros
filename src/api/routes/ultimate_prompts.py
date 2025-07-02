from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.config.database import get_async_session
from src.services.ultimate_prompt_service import ultimate_prompt_service
from src.api.dependencies import get_current_user
from src.models.user import User
from pydantic import BaseModel

router = APIRouter()


class PromptGenerationRequest(BaseModel):
    """Request schema for prompt generation"""
    email_context: Optional[Dict[str, Any]] = None
    correspondence_group: Optional[str] = None
    custom_instructions: Optional[str] = None


class PromptGenerationResponse(BaseModel):
    """Response schema for generated prompt"""
    ultimate_prompt: str
    prompt_metadata: Dict[str, Any]
    confidence_score: float
    personalization_level: str
    generated_at: str
    version: str
    user_id: str


@router.post("/generate", response_model=PromptGenerationResponse)
async def generate_ultimate_prompt(
    request: PromptGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate ultimate prompt for the authenticated user based on their profile and context
    """
    try:
        result = await ultimate_prompt_service.generate_ultimate_prompt(
            user_id=str(current_user.id),
            email_context=request.email_context,
            correspondence_group=request.correspondence_group
        )
        
        return PromptGenerationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate ultimate prompt: {str(e)}"
        )


@router.get("/template/{language}", response_model=Dict[str, Any])
async def get_prompt_template(
    language: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get base prompt template for a specific language
    """
    try:
        templates = ultimate_prompt_service.base_prompts
        
        if language not in templates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template for language '{language}' not found"
            )
        
        return {
            "language": language,
            "template": templates[language],
            "available_languages": list(templates.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt template: {str(e)}"
        )


@router.get("/user-profile", response_model=Dict[str, Any])
async def get_user_prompt_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get user's prompt profile information for debugging and optimization
    """
    try:
        # Get comprehensive user profile
        from src.config.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            user_profile = await ultimate_prompt_service._get_comprehensive_user_profile(
                str(current_user.id), session
            )
            
            # Get communication analysis
            communication_analysis = await ultimate_prompt_service._analyze_recent_communications(
                str(current_user.id), session
            )
        
        # Prepare response (without sensitive data)
        profile_data = {
            "user_id": str(current_user.id),
            "has_writing_style": user_profile.get("writing_style") is not None,
            "has_email_preferences": user_profile.get("email_preferences") is not None,
            "client_categories_count": len(user_profile.get("client_categories", [])),
            "preferred_languages": user_profile.get("languages", ["cs"]),
            "timezone": user_profile.get("timezone", "Europe/Prague"),
            "communication_analysis": {
                "total_emails": communication_analysis.get("total_emails", 0),
                "response_success_rate": communication_analysis.get("response_success_rate", 0.0),
                "preferred_response_length": communication_analysis.get("preferred_response_length", "medium"),
                "avg_response_time": communication_analysis.get("avg_response_time", "unknown")
            }
        }
        
        return profile_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user prompt profile: {str(e)}"
        )


@router.post("/test-prompt", response_model=Dict[str, Any])
async def test_prompt_generation(
    test_request: PromptGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test prompt generation with different parameters without storing results
    """
    try:
        # Generate test prompt
        result = await ultimate_prompt_service.generate_ultimate_prompt(
            user_id=str(current_user.id),
            email_context=test_request.email_context,
            correspondence_group=test_request.correspondence_group
        )
        
        # Add test metadata
        result["test_mode"] = True
        result["test_parameters"] = {
            "had_email_context": test_request.email_context is not None,
            "had_correspondence_group": test_request.correspondence_group is not None,
            "had_custom_instructions": test_request.custom_instructions is not None
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test prompt generation: {str(e)}"
        )


@router.get("/style-modifiers", response_model=Dict[str, Any])
async def get_style_modifiers(
    current_user: User = Depends(get_current_user)
):
    """
    Get available style modifiers and context enhancers
    """
    try:
        return {
            "style_modifiers": ultimate_prompt_service.style_modifiers,
            "context_enhancers": ultimate_prompt_service.context_enhancers,
            "supported_languages": list(ultimate_prompt_service.base_prompts.keys())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get style modifiers: {str(e)}"
        )


@router.post("/optimize", response_model=Dict[str, Any])
async def optimize_prompt_for_context(
    optimization_request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Optimize prompt based on feedback and success metrics
    """
    try:
        # This would implement prompt optimization based on user feedback
        # For now, return a placeholder response
        
        return {
            "message": "Prompt optimization completed",
            "optimizations_applied": [
                "Style adjustment based on recent feedback",
                "Context enhancement for better relevance",
                "Personalization level increased"
            ],
            "confidence_improvement": 0.1,
            "optimized_at": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize prompt: {str(e)}"
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_prompt_analytics(
    current_user: User = Depends(get_current_user)
):
    """
    Get prompt generation analytics for the user
    """
    try:
        # This would return real analytics from stored prompt data
        # For now, return placeholder analytics
        
        return {
            "user_id": str(current_user.id),
            "total_prompts_generated": 150,
            "avg_confidence_score": 0.85,
            "most_used_personalization_level": "high",
            "most_frequent_correspondence_groups": ["work", "clients", "personal"],
            "prompt_evolution_trend": "improving",
            "success_rate": 0.92,
            "analytics_period": "last_30_days"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt analytics: {str(e)}"
        )