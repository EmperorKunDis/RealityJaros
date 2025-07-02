"""
Email Monitoring Service

Provides minute-by-minute email monitoring and automated processing pipeline
as required by the Ultimate AI Email Agent specifications.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import AsyncSessionLocal
from src.models.user import User
from src.models.email import EmailMessage
from src.models.setup_wizard import EmailPreferences, AutomationConfiguration
from src.services.email_fetcher import EmailFetcherService
from src.services.auth_service import GoogleAuthService
from src.services.response_generator import ResponseGeneratorService
from src.services.background_tasks import task_manager

logger = logging.getLogger(__name__)


class EmailMonitoringService:
    """
    Service for continuous email monitoring and automated processing
    Implements the minute-by-minute monitoring required by the Ultimate AI Email Agent
    """
    
    def __init__(self):
        self.email_fetcher = EmailFetcherService()
        self.auth_service = GoogleAuthService()
        self.response_generator = ResponseGeneratorService()
    
    async def monitor_all_users(self) -> Dict[str, Any]:
        """
        Monitor emails for all active users with monitoring enabled
        This is called every minute by Celery beat
        """
        monitoring_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "users_monitored": 0,
            "new_emails_found": 0,
            "emails_processed": 0,
            "errors": []
        }
        
        try:
            async with AsyncSessionLocal() as session:
                # Get all active users with email sync enabled
                stmt = select(User).where(
                    and_(
                        User.is_active == True,
                        User.email_sync_enabled == True
                    )
                )
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                monitoring_results["users_monitored"] = len(users)
                
                # Monitor each user
                for user in users:
                    try:
                        user_result = await self._monitor_user_emails(user, session)
                        monitoring_results["new_emails_found"] += user_result["new_emails_found"]
                        monitoring_results["emails_processed"] += user_result["emails_processed"]
                        
                    except Exception as e:
                        error_msg = f"Error monitoring user {user.id}: {str(e)}"
                        logger.error(error_msg)
                        monitoring_results["errors"].append(error_msg)
                
                logger.info(f"Email monitoring completed: {monitoring_results}")
                return monitoring_results
                
        except Exception as e:
            error_msg = f"Critical error in email monitoring: {str(e)}"
            logger.error(error_msg)
            monitoring_results["errors"].append(error_msg)
            return monitoring_results
    
    async def _monitor_user_emails(self, user: User, session: AsyncSession) -> Dict[str, Any]:
        """Monitor emails for a specific user"""
        user_result = {
            "user_id": str(user.id),
            "new_emails_found": 0,
            "emails_processed": 0,
            "responses_generated": 0
        }
        
        try:
            # Get user's email preferences
            email_prefs = await self._get_user_email_preferences(user.id, session)
            
            # Check if it's within working hours (if configured)
            if email_prefs and not self._is_within_working_hours(email_prefs):
                logger.debug(f"Outside working hours for user {user.id}, skipping monitoring")
                return user_result
            
            # Get last sync time
            last_sync = user.last_sync or (datetime.utcnow() - timedelta(minutes=5))
            
            # Fetch new emails since last sync
            try:
                new_emails = await self.email_fetcher.fetch_new_emails(
                    user_id=str(user.id),
                    since_timestamp=last_sync
                )
                
                user_result["new_emails_found"] = len(new_emails)
                
                if new_emails:
                    # Process each new email
                    for email in new_emails:
                        try:
                            # Store email in database
                            await self._store_email(email, user.id, session)
                            
                            # Submit for background processing
                            await self._submit_email_processing(email, user.id)
                            
                            # Check if auto-response is enabled
                            automation_config = await self._get_user_automation_config(user.id, session)
                            if automation_config and automation_config.auto_respond_enabled:
                                response_generated = await self._handle_auto_response(email, user.id, automation_config)
                                if response_generated:
                                    user_result["responses_generated"] += 1
                            
                            user_result["emails_processed"] += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing email {email.message_id} for user {user.id}: {str(e)}")
                    
                    # Update user's last sync time
                    user.last_sync = datetime.utcnow()
                    await session.commit()
                    
                    logger.info(f"Processed {len(new_emails)} new emails for user {user.id}")
                
            except Exception as e:
                logger.error(f"Error fetching emails for user {user.id}: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Error in user email monitoring for {user.id}: {str(e)}")
            raise
        
        return user_result
    
    async def _get_user_email_preferences(self, user_id: str, session: AsyncSession) -> Optional[EmailPreferences]:
        """Get user's email preferences"""
        try:
            stmt = select(EmailPreferences).where(EmailPreferences.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting email preferences for user {user_id}: {str(e)}")
            return None
    
    async def _get_user_automation_config(self, user_id: str, session: AsyncSession) -> Optional[AutomationConfiguration]:
        """Get user's automation configuration"""
        try:
            stmt = select(AutomationConfiguration).where(AutomationConfiguration.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting automation config for user {user_id}: {str(e)}")
            return None
    
    def _is_within_working_hours(self, email_prefs: EmailPreferences) -> bool:
        """Check if current time is within user's working hours"""
        try:
            if not email_prefs.working_hours_start or not email_prefs.working_hours_end:
                return True  # No working hours restriction
            
            now = datetime.now()
            current_weekday = now.strftime('%A').lower()
            
            # Check if today is a working day
            if current_weekday not in email_prefs.working_days:
                return False
            
            # Parse working hours
            start_time = datetime.strptime(email_prefs.working_hours_start, '%H:%M').time()
            end_time = datetime.strptime(email_prefs.working_hours_end, '%H:%M').time()
            current_time = now.time()
            
            # Check if within working hours
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                # Handle overnight working hours (e.g., 22:00 to 06:00)
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            logger.error(f"Error checking working hours: {str(e)}")
            return True  # Default to allowing monitoring if error occurs
    
    async def _store_email(self, email_data: Dict[str, Any], user_id: str, session: AsyncSession) -> EmailMessage:
        """Store email in database"""
        try:
            # Check if email already exists
            stmt = select(EmailMessage).where(
                and_(
                    EmailMessage.message_id == email_data["message_id"],
                    EmailMessage.user_id == user_id
                )
            )
            result = await session.execute(stmt)
            existing_email = result.scalar_one_or_none()
            
            if existing_email:
                return existing_email
            
            # Create new email record
            email = EmailMessage(
                user_id=user_id,
                message_id=email_data["message_id"],
                thread_id=email_data.get("thread_id"),
                sender=email_data["sender"],
                recipient=email_data["recipient"],
                subject=email_data["subject"],
                body=email_data["body"],
                timestamp=email_data["timestamp"],
                direction="incoming",  # All monitored emails are incoming
                labels=email_data.get("labels", []),
                attachments=email_data.get("attachments", [])
            )
            
            session.add(email)
            await session.flush()  # Get the ID without committing
            
            return email
            
        except Exception as e:
            logger.error(f"Error storing email {email_data.get('message_id')}: {str(e)}")
            raise
    
    async def _submit_email_processing(self, email_data: Dict[str, Any], user_id: str) -> None:
        """Submit email for background processing (analysis, vectorization)"""
        try:
            # Submit for email analysis
            await task_manager.submit_email_analysis(
                email_id=email_data["message_id"],
                user_id=user_id,
                priority="normal"
            )
            
            # Submit for vectorization (for RAG)
            await task_manager.submit_vectorization(
                email_ids=[email_data["message_id"]],
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error submitting email processing for {email_data.get('message_id')}: {str(e)}")
            raise
    
    async def _handle_auto_response(
        self, 
        email_data: Dict[str, Any], 
        user_id: str, 
        automation_config: AutomationConfiguration
    ) -> bool:
        """Handle automatic response generation and sending"""
        try:
            # Check auto-response conditions
            if not self._should_auto_respond(email_data, automation_config):
                return False
            
            # Check daily limit
            if not await self._check_daily_response_limit(user_id, automation_config):
                logger.warning(f"Daily auto-response limit reached for user {user_id}")
                return False
            
            # Schedule response generation (without delay in monitoring - delay will be handled by auto-send service)
            await task_manager.submit_response_generation(
                email_id=email_data["message_id"],
                user_id=user_id,
                options={
                    "auto_send": True,
                    "confidence_threshold": automation_config.auto_respond_confidence_threshold,
                    "require_confirmation": automation_config.require_confirmation_for_important,
                    "response_delay_minutes": automation_config.auto_respond_delay_minutes
                }
            )
            
            logger.info(f"Auto-response scheduled for email {email_data.get('message_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error in auto-response handling for {email_data.get('message_id')}: {str(e)}")
            return False
    
    def _should_auto_respond(self, email_data: Dict[str, Any], automation_config: AutomationConfiguration) -> bool:
        """Determine if email should receive auto-response"""
        try:
            # Skip auto-response for marketing emails, notifications, etc.
            subject_lower = email_data["subject"].lower()
            body_lower = email_data["body"].lower()
            
            # Skip obvious automated emails
            automated_indicators = [
                "no-reply", "noreply", "donotreply", "automated", "notification",
                "unsubscribe", "newsletter", "marketing", "promotion"
            ]
            
            sender_lower = email_data["sender"].lower()
            for indicator in automated_indicators:
                if indicator in sender_lower or indicator in subject_lower:
                    return False
            
            # Skip if email contains auto-reply indicators
            auto_reply_indicators = [
                "out of office", "vacation", "away", "automatic reply",
                "auto-reply", "autoreply", "away message"
            ]
            
            for indicator in auto_reply_indicators:
                if indicator in subject_lower or indicator in body_lower:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking auto-response conditions: {str(e)}")
            return False
    
    async def _check_daily_response_limit(self, user_id: str, automation_config: AutomationConfiguration) -> bool:
        """Check if daily auto-response limit has been reached"""
        try:
            async with AsyncSessionLocal() as session:
                today = datetime.utcnow().date()
                
                # Count responses sent today
                from src.models.response import GeneratedResponse
                stmt = select(GeneratedResponse).where(
                    and_(
                        GeneratedResponse.user_id == user_id,
                        GeneratedResponse.status == "sent",
                        GeneratedResponse.sent_at >= today
                    )
                )
                result = await session.execute(stmt)
                today_responses = len(result.scalars().all())
                
                return today_responses < automation_config.maximum_auto_responses_per_day
                
        except Exception as e:
            logger.error(f"Error checking daily response limit for user {user_id}: {str(e)}")
            return False
    
    async def generate_daily_summary(self, user_id: str) -> Dict[str, Any]:
        """Generate daily summary for a user"""
        try:
            async with AsyncSessionLocal() as session:
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                
                # Get emails from yesterday
                stmt = select(EmailMessage).where(
                    and_(
                        EmailMessage.user_id == user_id,
                        EmailMessage.timestamp >= yesterday,
                        EmailMessage.timestamp < yesterday + timedelta(days=1)
                    )
                )
                result = await session.execute(stmt)
                emails = result.scalars().all()
                
                # Get responses from yesterday
                from src.models.response import GeneratedResponse
                stmt = select(GeneratedResponse).where(
                    and_(
                        GeneratedResponse.user_id == user_id,
                        GeneratedResponse.created_at >= yesterday,
                        GeneratedResponse.created_at < yesterday + timedelta(days=1)
                    )
                )
                result = await session.execute(stmt)
                responses = result.scalars().all()
                
                summary = {
                    "date": yesterday.isoformat(),
                    "user_id": user_id,
                    "emails_received": len([e for e in emails if e.direction == "incoming"]),
                    "emails_sent": len([e for e in emails if e.direction == "outgoing"]),
                    "auto_responses_generated": len([r for r in responses if r.is_auto_generated]),
                    "auto_responses_sent": len([r for r in responses if r.status == "sent" and r.is_auto_generated]),
                    "manual_responses": len([r for r in responses if not r.is_auto_generated]),
                    "top_contacts": self._get_top_contacts(emails),
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error generating daily summary for user {user_id}: {str(e)}")
            raise
    
    def _get_top_contacts(self, emails: List[EmailMessage]) -> List[Dict[str, Any]]:
        """Get top contacts from email list"""
        try:
            contact_counts = {}
            
            for email in emails:
                if email.direction == "incoming":
                    contact = email.sender
                else:
                    contact = email.recipient
                
                if contact:
                    contact_counts[contact] = contact_counts.get(contact, 0) + 1
            
            # Sort by count and return top 5
            top_contacts = sorted(contact_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return [{"email": contact, "count": count} for contact, count in top_contacts]
            
        except Exception as e:
            logger.error(f"Error getting top contacts: {str(e)}")
            return []


# Global instance
email_monitoring_service = EmailMonitoringService()