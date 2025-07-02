import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.setup_wizard import (
    SetupWizardProgress,
    EmailPreferences,
    WritingStyleConfiguration,
    ClientCategoryConfiguration,
    AutomationConfiguration,
    NotificationConfiguration,
    IntegrationConfiguration
)
from src.models.user import User
from src.schemas.setup_wizard import (
    SetupWizardProgressSchema,
    EmailPreferencesSchema,
    WritingStyleConfigurationSchema,
    ClientCategoryConfigurationSchema,
    AutomationConfigurationSchema,
    NotificationConfigurationSchema,
    IntegrationConfigurationSchema,
    SetupWizardCompleteResponse
)

logger = logging.getLogger(__name__)


class SetupWizardService:
    """
    Service for managing the 8-step setup wizard process
    Handles user onboarding and configuration
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_or_create_wizard_progress(self, user_id: str) -> SetupWizardProgress:
        """Get existing wizard progress or create new one"""
        try:
            # Try to get existing progress
            result = await self.db.execute(
                select(SetupWizardProgress).where(SetupWizardProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if not progress:
                # Create new progress record
                progress = SetupWizardProgress(user_id=user_id)
                self.db.add(progress)
                await self.db.commit()
                await self.db.refresh(progress)
                logger.info(f"Created new setup wizard progress for user {user_id}")
            
            return progress
        except Exception as e:
            logger.error(f"Error getting/creating wizard progress for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_1_google_auth(self, user_id: str, auth_data: Dict[str, Any]) -> bool:
        """Complete step 1: Google authentication"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Verify Google authentication is successful
            if auth_data.get("google_authenticated") and auth_data.get("gmail_access"):
                progress.step_1_google_auth = True
                progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 1 else progress.current_step
                
                await self.db.commit()
                logger.info(f"Step 1 (Google Auth) completed for user {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error completing step 1 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_2_email_preferences(
        self, 
        user_id: str, 
        preferences_data: EmailPreferencesSchema
    ) -> bool:
        """Complete step 2: Email preferences configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Create or update email preferences
            result = await self.db.execute(
                select(EmailPreferences).where(EmailPreferences.user_id == user_id)
            )
            preferences = result.scalar_one_or_none()
            
            if preferences:
                # Update existing preferences
                for field, value in preferences_data.dict().items():
                    setattr(preferences, field, value)
            else:
                # Create new preferences
                preferences = EmailPreferences(user_id=user_id, **preferences_data.dict())
                self.db.add(preferences)
            
            progress.step_2_email_preferences = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 2 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 2 (Email Preferences) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 2 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_3_writing_style(
        self, 
        user_id: str, 
        style_data: WritingStyleConfigurationSchema
    ) -> bool:
        """Complete step 3: Writing style configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Create or update writing style configuration
            result = await self.db.execute(
                select(WritingStyleConfiguration).where(WritingStyleConfiguration.user_id == user_id)
            )
            style_config = result.scalar_one_or_none()
            
            if style_config:
                # Update existing configuration
                for field, value in style_data.dict().items():
                    setattr(style_config, field, value)
            else:
                # Create new configuration
                style_config = WritingStyleConfiguration(user_id=user_id, **style_data.dict())
                self.db.add(style_config)
            
            progress.step_3_writing_style = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 3 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 3 (Writing Style) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 3 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_4_client_categories(
        self, 
        user_id: str, 
        categories_data: List[ClientCategoryConfigurationSchema]
    ) -> bool:
        """Complete step 4: Client categories configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Delete existing categories for this user
            await self.db.execute(
                select(ClientCategoryConfiguration).where(ClientCategoryConfiguration.user_id == user_id)
            )
            
            # Create new categories
            for category_data in categories_data:
                category = ClientCategoryConfiguration(user_id=user_id, **category_data.dict())
                self.db.add(category)
            
            progress.step_4_client_categories = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 4 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 4 (Client Categories) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 4 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_5_automation(
        self, 
        user_id: str, 
        automation_data: AutomationConfigurationSchema
    ) -> bool:
        """Complete step 5: Response automation configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Create or update automation configuration
            result = await self.db.execute(
                select(AutomationConfiguration).where(AutomationConfiguration.user_id == user_id)
            )
            automation_config = result.scalar_one_or_none()
            
            if automation_config:
                # Update existing configuration
                for field, value in automation_data.dict().items():
                    setattr(automation_config, field, value)
            else:
                # Create new configuration
                automation_config = AutomationConfiguration(user_id=user_id, **automation_data.dict())
                self.db.add(automation_config)
            
            progress.step_5_response_automation = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 5 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 5 (Automation) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 5 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_6_notifications(
        self, 
        user_id: str, 
        notification_data: NotificationConfigurationSchema
    ) -> bool:
        """Complete step 6: Notifications configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Create or update notification configuration
            result = await self.db.execute(
                select(NotificationConfiguration).where(NotificationConfiguration.user_id == user_id)
            )
            notification_config = result.scalar_one_or_none()
            
            if notification_config:
                # Update existing configuration
                for field, value in notification_data.dict().items():
                    setattr(notification_config, field, value)
            else:
                # Create new configuration
                notification_config = NotificationConfiguration(user_id=user_id, **notification_data.dict())
                self.db.add(notification_config)
            
            progress.step_6_notifications = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 6 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 6 (Notifications) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 6 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_7_integrations(
        self, 
        user_id: str, 
        integration_data: IntegrationConfigurationSchema
    ) -> bool:
        """Complete step 7: Integrations configuration"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Create or update integration configuration
            result = await self.db.execute(
                select(IntegrationConfiguration).where(IntegrationConfiguration.user_id == user_id)
            )
            integration_config = result.scalar_one_or_none()
            
            if integration_config:
                # Update existing configuration
                for field, value in integration_data.dict().items():
                    setattr(integration_config, field, value)
            else:
                # Create new configuration
                integration_config = IntegrationConfiguration(user_id=user_id, **integration_data.dict())
                self.db.add(integration_config)
            
            progress.step_7_integrations = True
            progress.current_step = min(progress.current_step + 1, 8) if progress.current_step == 7 else progress.current_step
            
            await self.db.commit()
            logger.info(f"Step 7 (Integrations) completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing step 7 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def complete_step_8_verification(self, user_id: str, verification_data: Dict[str, Any]) -> bool:
        """Complete step 8: Final verification and testing"""
        try:
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Perform verification checks
            verification_passed = await self._perform_verification_checks(user_id)
            
            if verification_passed:
                progress.step_8_verification = True
                progress.current_step = 8
                progress.is_completed = True
                progress.completed_at = datetime.now()
                
                await self.db.commit()
                logger.info(f"Step 8 (Verification) completed for user {user_id} - Setup wizard finished!")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error completing step 8 for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def _perform_verification_checks(self, user_id: str) -> bool:
        """Perform comprehensive verification checks"""
        try:
            # Check if user has completed all required steps
            progress = await self.get_or_create_wizard_progress(user_id)
            
            required_steps = [
                progress.step_1_google_auth,
                progress.step_2_email_preferences,
                progress.step_3_writing_style,
                progress.step_5_response_automation,
                progress.step_6_notifications,
                progress.step_7_integrations
            ]
            
            # Step 4 (client categories) is optional
            
            all_required_complete = all(required_steps)
            
            if all_required_complete:
                logger.info(f"All verification checks passed for user {user_id}")
                return True
            
            logger.warning(f"Verification checks failed for user {user_id}: {required_steps}")
            return False
            
        except Exception as e:
            logger.error(f"Error during verification checks for user {user_id}: {str(e)}")
            return False
    
    async def get_wizard_status(self, user_id: str) -> SetupWizardCompleteResponse:
        """Get complete wizard status for a user"""
        try:
            # Load user with all setup wizard relationships
            result = await self.db.execute(
                select(User)
                .where(User.id == user_id)
                .options(
                    selectinload(User.setup_wizard_progress),
                    selectinload(User.email_preferences),
                    selectinload(User.writing_style_configuration),
                    selectinload(User.client_category_configurations),
                    selectinload(User.automation_configuration),
                    selectinload(User.notification_configuration),
                    selectinload(User.integration_configuration)
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create progress if it doesn't exist
            if not user.setup_wizard_progress:
                await self.get_or_create_wizard_progress(user_id)
                # Reload user with progress
                result = await self.db.execute(
                    select(User)
                    .where(User.id == user_id)
                    .options(selectinload(User.setup_wizard_progress))
                )
                user = result.scalar_one()
            
            # Build response
            response = SetupWizardCompleteResponse(
                user_id=user_id,
                is_completed=user.setup_wizard_progress.is_completed if user.setup_wizard_progress else False,
                completed_at=user.setup_wizard_progress.completed_at if user.setup_wizard_progress else None,
                progress=SetupWizardProgressSchema.from_orm(user.setup_wizard_progress) if user.setup_wizard_progress else None,
                email_preferences=EmailPreferencesSchema.from_orm(user.email_preferences) if user.email_preferences else None,
                writing_style_configuration=WritingStyleConfigurationSchema.from_orm(user.writing_style_configuration) if user.writing_style_configuration else None,
                client_categories=[ClientCategoryConfigurationSchema.from_orm(cat) for cat in user.client_category_configurations] if user.client_category_configurations else [],
                automation_configuration=AutomationConfigurationSchema.from_orm(user.automation_configuration) if user.automation_configuration else None,
                notification_configuration=NotificationConfigurationSchema.from_orm(user.notification_configuration) if user.notification_configuration else None,
                integration_configuration=IntegrationConfigurationSchema.from_orm(user.integration_configuration) if user.integration_configuration else None
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting wizard status for user {user_id}: {str(e)}")
            raise
    
    async def reset_wizard_progress(self, user_id: str) -> bool:
        """Reset wizard progress for a user (admin function)"""
        try:
            # Delete all setup wizard related data
            progress = await self.get_or_create_wizard_progress(user_id)
            
            # Reset progress to initial state
            progress.step_1_google_auth = False
            progress.step_2_email_preferences = False
            progress.step_3_writing_style = False
            progress.step_4_client_categories = False
            progress.step_5_response_automation = False
            progress.step_6_notifications = False
            progress.step_7_integrations = False
            progress.step_8_verification = False
            progress.current_step = 1
            progress.is_completed = False
            progress.completed_at = None
            
            await self.db.commit()
            logger.info(f"Setup wizard progress reset for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting wizard progress for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise