from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from src.config.database import get_async_session
from src.services.setup_wizard_service import SetupWizardService
from src.schemas.setup_wizard import (
    SetupWizardProgressSchema,
    EmailPreferencesSchema,
    WritingStyleConfigurationSchema,
    ClientCategoryConfigurationSchema,
    AutomationConfigurationSchema,
    NotificationConfigurationSchema,
    IntegrationConfigurationSchema,
    SetupWizardStepRequest,
    SetupWizardStepResponse,
    SetupWizardCompleteResponse
)
from src.api.dependencies import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/status", response_model=SetupWizardCompleteResponse)
async def get_setup_wizard_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current setup wizard status for the authenticated user
    """
    try:
        service = SetupWizardService(db)
        status = await service.get_wizard_status(str(current_user.id))
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get setup wizard status: {str(e)}"
        )


@router.post("/step/1", response_model=SetupWizardStepResponse)
async def complete_step_1_google_auth(
    auth_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 1: Google Authentication and Gmail Access
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_1_google_auth(str(current_user.id), auth_data)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Google authentication completed successfully",
                current_step=1,
                next_step=2
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Google authentication verification failed",
                current_step=1
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 1: {str(e)}"
        )


@router.post("/step/2", response_model=SetupWizardStepResponse)
async def complete_step_2_email_preferences(
    preferences: EmailPreferencesSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 2: Email Preferences Configuration
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_2_email_preferences(str(current_user.id), preferences)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Email preferences configured successfully",
                current_step=2,
                next_step=3
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure email preferences",
                current_step=2
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 2: {str(e)}"
        )


@router.post("/step/3", response_model=SetupWizardStepResponse)
async def complete_step_3_writing_style(
    style_config: WritingStyleConfigurationSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 3: Writing Style Configuration
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_3_writing_style(str(current_user.id), style_config)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Writing style configured successfully",
                current_step=3,
                next_step=4
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure writing style",
                current_step=3
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 3: {str(e)}"
        )


@router.post("/step/4", response_model=SetupWizardStepResponse)
async def complete_step_4_client_categories(
    categories: List[ClientCategoryConfigurationSchema],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 4: Client Categories Configuration (Optional)
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_4_client_categories(str(current_user.id), categories)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Client categories configured successfully",
                current_step=4,
                next_step=5
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure client categories",
                current_step=4
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 4: {str(e)}"
        )


@router.post("/step/5", response_model=SetupWizardStepResponse)
async def complete_step_5_automation(
    automation_config: AutomationConfigurationSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 5: Response Automation Configuration
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_5_automation(str(current_user.id), automation_config)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Automation configured successfully",
                current_step=5,
                next_step=6
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure automation",
                current_step=5
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 5: {str(e)}"
        )


@router.post("/step/6", response_model=SetupWizardStepResponse)
async def complete_step_6_notifications(
    notification_config: NotificationConfigurationSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 6: Notifications Configuration
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_6_notifications(str(current_user.id), notification_config)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Notifications configured successfully",
                current_step=6,
                next_step=7
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure notifications",
                current_step=6
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 6: {str(e)}"
        )


@router.post("/step/7", response_model=SetupWizardStepResponse)
async def complete_step_7_integrations(
    integration_config: IntegrationConfigurationSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 7: Integrations Configuration
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_7_integrations(str(current_user.id), integration_config)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Integrations configured successfully",
                current_step=7,
                next_step=8
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Failed to configure integrations",
                current_step=7
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 7: {str(e)}"
        )


@router.post("/step/8", response_model=SetupWizardStepResponse)
async def complete_step_8_verification(
    verification_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete Step 8: Final Verification and Testing
    """
    try:
        service = SetupWizardService(db)
        success = await service.complete_step_8_verification(str(current_user.id), verification_data)
        
        if success:
            return SetupWizardStepResponse(
                success=True,
                message="Setup wizard completed successfully! Welcome to AI Email Assistant.",
                current_step=8,
                is_completed=True
            )
        else:
            return SetupWizardStepResponse(
                success=False,
                message="Verification failed. Please complete all required steps.",
                current_step=8
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete step 8: {str(e)}"
        )


@router.post("/reset", response_model=Dict[str, str])
async def reset_setup_wizard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Reset setup wizard progress (for testing or re-configuration)
    """
    try:
        service = SetupWizardService(db)
        success = await service.reset_wizard_progress(str(current_user.id))
        
        if success:
            return {"message": "Setup wizard progress reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset setup wizard progress"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset setup wizard: {str(e)}"
        )


@router.post("/complete", response_model=SetupWizardCompleteResponse)
async def complete_entire_wizard(
    wizard_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Complete entire wizard in one request (advanced users)
    """
    try:
        service = SetupWizardService(db)
        
        # Process each step sequentially
        steps_completed = 0
        
        # Step 1: Google Auth
        if "google_auth" in wizard_data:
            await service.complete_step_1_google_auth(str(current_user.id), wizard_data["google_auth"])
            steps_completed += 1
        
        # Step 2: Email Preferences
        if "email_preferences" in wizard_data:
            preferences = EmailPreferencesSchema(**wizard_data["email_preferences"])
            await service.complete_step_2_email_preferences(str(current_user.id), preferences)
            steps_completed += 1
        
        # Step 3: Writing Style
        if "writing_style" in wizard_data:
            style_config = WritingStyleConfigurationSchema(**wizard_data["writing_style"])
            await service.complete_step_3_writing_style(str(current_user.id), style_config)
            steps_completed += 1
        
        # Step 4: Client Categories (optional)
        if "client_categories" in wizard_data:
            categories = [ClientCategoryConfigurationSchema(**cat) for cat in wizard_data["client_categories"]]
            await service.complete_step_4_client_categories(str(current_user.id), categories)
            steps_completed += 1
        
        # Step 5: Automation
        if "automation" in wizard_data:
            automation_config = AutomationConfigurationSchema(**wizard_data["automation"])
            await service.complete_step_5_automation(str(current_user.id), automation_config)
            steps_completed += 1
        
        # Step 6: Notifications
        if "notifications" in wizard_data:
            notification_config = NotificationConfigurationSchema(**wizard_data["notifications"])
            await service.complete_step_6_notifications(str(current_user.id), notification_config)
            steps_completed += 1
        
        # Step 7: Integrations
        if "integrations" in wizard_data:
            integration_config = IntegrationConfigurationSchema(**wizard_data["integrations"])
            await service.complete_step_7_integrations(str(current_user.id), integration_config)
            steps_completed += 1
        
        # Step 8: Verification
        verification_data = wizard_data.get("verification", {})
        await service.complete_step_8_verification(str(current_user.id), verification_data)
        steps_completed += 1
        
        # Return complete status
        return await service.get_wizard_status(str(current_user.id))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete wizard: {str(e)}"
        )