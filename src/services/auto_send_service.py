"""
Automatic Email Sending Service

Implements configurable automatic email sending with safety checks,
daily summaries, and confirmation workflows as required by the 
Ultimate AI Email Agent specifications.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import AsyncSessionLocal
from src.models.user import User
from src.models.email import EmailMessage
from src.models.response import GeneratedResponse
from src.models.setup_wizard import AutomationConfiguration, NotificationConfiguration
from src.services.auth_service import GoogleAuthService
from src.services.response_generator import ResponseGeneratorService

logger = logging.getLogger(__name__)


class AutoSendService:
    """
    Service for automatic email sending with intelligent safety checks
    Implements the automatic sending requirements from the Czech design document
    """
    
    def __init__(self):
        self.auth_service = GoogleAuthService()
        self.response_generator = ResponseGeneratorService()
        self.daily_limits = {}  # Cache for daily limits
    
    async def process_auto_send_queue(self) -> Dict[str, Any]:
        """
        Process the queue of emails waiting for auto-send
        Called periodically by background tasks
        """
        processing_results = {
            "timestamp": datetime.now().isoformat(),
            "emails_processed": 0,
            "emails_sent": 0,
            "emails_held": 0,
            "errors": []
        }
        
        try:
            async with AsyncSessionLocal() as session:
                # Get all pending auto-send responses
                pending_responses = await self._get_pending_auto_responses(session)
                processing_results["emails_processed"] = len(pending_responses)
                
                for response in pending_responses:
                    try:
                        # Check if email should be auto-sent
                        should_send = await self._should_auto_send_email(response, session)
                        
                        if should_send:
                            # Send the email
                            send_result = await self._send_email_response(response, session)
                            
                            if send_result["success"]:
                                processing_results["emails_sent"] += 1
                                logger.info(f"Auto-sent email response {response.id}")
                            else:
                                processing_results["errors"].append(
                                    f"Failed to send response {response.id}: {send_result['error']}"
                                )
                        else:
                            processing_results["emails_held"] += 1
                            logger.debug(f"Held email response {response.id} for manual review")
                    
                    except Exception as e:
                        error_msg = f"Error processing response {response.id}: {str(e)}"
                        logger.error(error_msg)
                        processing_results["errors"].append(error_msg)
                
                logger.info(f"Auto-send processing completed: {processing_results}")
                return processing_results
                
        except Exception as e:
            error_msg = f"Critical error in auto-send processing: {str(e)}"
            logger.error(error_msg)
            processing_results["errors"].append(error_msg)
            return processing_results
    
    async def _get_pending_auto_responses(self, session: AsyncSession) -> List[GeneratedResponse]:
        """Get all responses pending auto-send"""
        try:
            # Get responses that are:
            # 1. Generated and ready
            # 2. Have auto_send enabled
            # 3. Haven't been sent yet
            # 4. Meet confidence threshold
            # 5. Have passed any required delay
            
            delay_threshold = datetime.now() - timedelta(minutes=5)  # Default 5-minute delay
            
            stmt = select(GeneratedResponse).where(
                and_(
                    GeneratedResponse.status == "pending_auto_send",
                    GeneratedResponse.is_auto_generated == True,
                    GeneratedResponse.created_at <= delay_threshold,
                    GeneratedResponse.confidence_score >= 0.7  # Minimum confidence
                )
            ).order_by(GeneratedResponse.created_at)
            
            result = await session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting pending auto responses: {str(e)}")
            return []
    
    async def _should_auto_send_email(self, response: GeneratedResponse, session: AsyncSession) -> bool:
        """Determine if email should be automatically sent"""
        try:
            # Get user's automation configuration
            automation_config = await self._get_user_automation_config(response.user_id, session)
            
            if not automation_config or not automation_config.auto_respond_enabled:
                return False
            
            # Check confidence threshold
            if response.confidence_score < automation_config.auto_respond_confidence_threshold / 100.0:
                logger.debug(f"Response {response.id} below confidence threshold")
                return False
            
            # Check daily limit
            if not await self._check_daily_send_limit(response.user_id, automation_config, session):
                logger.warning(f"Daily send limit reached for user {response.user_id}")
                return False
            
            # Check if requires confirmation for important emails
            if automation_config.require_confirmation_for_important:
                if await self._is_important_email(response, session):
                    logger.info(f"Important email {response.id} held for manual confirmation")
                    await self._mark_for_manual_review(response, "important_email", session)
                    return False
            
            # Check business hours if configured
            if not await self._is_within_business_hours(response.user_id, session):
                logger.debug(f"Outside business hours for user {response.user_id}")
                return False
            
            # All checks passed
            return True
            
        except Exception as e:
            logger.error(f"Error checking auto-send conditions for response {response.id}: {str(e)}")
            return False
    
    async def _send_email_response(self, response: GeneratedResponse, session: AsyncSession) -> Dict[str, Any]:
        """Send the email response via Gmail API"""
        try:
            # Get the original email to reply to
            original_email = await self._get_original_email(response.original_email_id, session)
            if not original_email:
                return {"success": False, "error": "Original email not found"}
            
            # Get user authentication
            user = await self._get_user(response.user_id, session)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Prepare email content
            email_content = await self._prepare_email_content(
                response, original_email, user, session
            )
            
            # Send via Gmail API
            send_result = await self._send_via_gmail_api(
                user_id=response.user_id,
                email_content=email_content,
                original_email=original_email
            )
            
            if send_result["success"]:
                # Update response status
                response.status = "sent"
                response.sent_at = datetime.now()
                response.gmail_message_id = send_result.get("message_id")
                
                await session.commit()
                
                # Log the successful send
                await self._log_email_send(response, send_result, session)
                
                return {"success": True, "message_id": send_result.get("message_id")}
            else:
                # Mark as failed
                response.status = "send_failed"
                response.error_message = send_result.get("error", "Unknown send error")
                await session.commit()
                
                return {"success": False, "error": send_result.get("error")}
                
        except Exception as e:
            logger.error(f"Error sending email response {response.id}: {str(e)}")
            
            # Mark as failed
            try:
                response.status = "send_failed"
                response.error_message = str(e)
                await session.commit()
            except:
                pass
            
            return {"success": False, "error": str(e)}
    
    async def _get_user_automation_config(self, user_id: str, session: AsyncSession) -> Optional[AutomationConfiguration]:
        """Get user's automation configuration"""
        try:
            stmt = select(AutomationConfiguration).where(AutomationConfiguration.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting automation config for user {user_id}: {str(e)}")
            return None
    
    async def _check_daily_send_limit(self, user_id: str, automation_config: AutomationConfiguration, session: AsyncSession) -> bool:
        """Check if daily send limit has been reached"""
        try:
            today = datetime.now().date()
            
            # Count emails sent today
            stmt = select(func.count(GeneratedResponse.id)).where(
                and_(
                    GeneratedResponse.user_id == user_id,
                    GeneratedResponse.status == "sent",
                    func.date(GeneratedResponse.sent_at) == today
                )
            )
            result = await session.execute(stmt)
            today_count = result.scalar() or 0
            
            return today_count < automation_config.maximum_auto_responses_per_day
            
        except Exception as e:
            logger.error(f"Error checking daily send limit for user {user_id}: {str(e)}")
            return False
    
    async def _is_important_email(self, response: GeneratedResponse, session: AsyncSession) -> bool:
        """Determine if email is important and requires manual confirmation"""
        try:
            original_email = await self._get_original_email(response.original_email_id, session)
            if not original_email:
                return False
            
            # Check for importance indicators
            important_indicators = [
                "urgent", "important", "critical", "asap", "emergency",
                "contract", "legal", "invoice", "payment", "deadline",
                "naléhavé", "důležité", "kritické", "smlouva", "platba"
            ]
            
            content = f"{original_email.subject} {original_email.body}".lower()
            
            for indicator in important_indicators:
                if indicator in content:
                    return True
            
            # Check sender importance (could be based on domain or previous interactions)
            important_domains = ["@boss.com", "@client.com", "@lawyer.com"]
            sender_email = original_email.sender.lower()
            
            for domain in important_domains:
                if domain in sender_email:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking email importance: {str(e)}")
            return True  # Err on the side of caution
    
    async def _is_within_business_hours(self, user_id: str, session: AsyncSession) -> bool:
        """Check if current time is within user's business hours"""
        try:
            from src.models.setup_wizard import EmailPreferences
            
            stmt = select(EmailPreferences).where(EmailPreferences.user_id == user_id)
            result = await session.execute(stmt)
            email_prefs = result.scalar_one_or_none()
            
            if not email_prefs:
                return True  # No restrictions if no preferences set
            
            now = datetime.now()
            current_weekday = now.strftime('%A').lower()
            
            # Check if today is a working day
            if current_weekday not in email_prefs.working_days:
                return False
            
            # Check working hours
            if email_prefs.working_hours_start and email_prefs.working_hours_end:
                start_time = datetime.strptime(email_prefs.working_hours_start, '%H:%M').time()
                end_time = datetime.strptime(email_prefs.working_hours_end, '%H:%M').time()
                current_time = now.time()
                
                if start_time <= end_time:
                    return start_time <= current_time <= end_time
                else:
                    # Handle overnight hours
                    return current_time >= start_time or current_time <= end_time
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking business hours for user {user_id}: {str(e)}")
            return True
    
    async def _mark_for_manual_review(self, response: GeneratedResponse, reason: str, session: AsyncSession) -> None:
        """Mark response for manual review"""
        try:
            response.status = "manual_review_required"
            response.review_reason = reason
            response.review_requested_at = datetime.now()
            await session.commit()
            
            # Could send notification to user here
            logger.info(f"Response {response.id} marked for manual review: {reason}")
            
        except Exception as e:
            logger.error(f"Error marking response for manual review: {str(e)}")
    
    async def _get_original_email(self, email_id: str, session: AsyncSession) -> Optional[EmailMessage]:
        """Get the original email being replied to"""
        try:
            stmt = select(EmailMessage).where(EmailMessage.id == email_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting original email {email_id}: {str(e)}")
            return None
    
    async def _get_user(self, user_id: str, session: AsyncSession) -> Optional[User]:
        """Get user information"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None
    
    async def _prepare_email_content(
        self, 
        response: GeneratedResponse, 
        original_email: EmailMessage,
        user: User,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Prepare email content for sending"""
        try:
            # Get user's email preferences for signature, etc.
            from src.models.setup_wizard import WritingStyleConfiguration
            
            style_stmt = select(WritingStyleConfiguration).where(
                WritingStyleConfiguration.user_id == user.id
            )
            style_result = await session.execute(style_stmt)
            style_config = style_result.scalar_one_or_none()
            
            # Build email content
            subject = f"Re: {original_email.subject}"
            if original_email.subject.startswith("Re:"):
                subject = original_email.subject
            
            # Add signature based on user preferences
            body = response.response_text
            if style_config:
                signature = self._generate_signature(user, style_config)
                if signature:
                    body = f"{body}\n\n{signature}"
            
            return {
                "to": original_email.sender,
                "subject": subject,
                "body": body,
                "in_reply_to": original_email.message_id,
                "thread_id": original_email.thread_id
            }
            
        except Exception as e:
            logger.error(f"Error preparing email content: {str(e)}")
            raise
    
    def _generate_signature(self, user: User, style_config: WritingStyleConfiguration) -> Optional[str]:
        """Generate email signature based on user preferences"""
        try:
            if style_config.signature_style == "minimal":
                return user.display_name or user.email.split('@')[0]
            elif style_config.signature_style == "standard":
                return f"{user.display_name or 'Uživatel'}\n{user.email}"
            elif style_config.signature_style == "detailed":
                return f"{user.display_name or 'Uživatel'}\n{user.email}\n\n--\nOdeslané pomocí AI Email Assistant"
            else:
                return None
        except Exception as e:
            logger.error(f"Error generating signature: {str(e)}")
            return None
    
    async def _send_via_gmail_api(
        self, 
        user_id: str, 
        email_content: Dict[str, Any],
        original_email: EmailMessage
    ) -> Dict[str, Any]:
        """Send email via Gmail API"""
        try:
            # This would integrate with the actual Gmail API
            # For now, simulate the sending process
            
            logger.info(f"Sending email via Gmail API for user {user_id}")
            logger.debug(f"Email content: {email_content}")
            
            # Simulate successful send
            return {
                "success": True,
                "message_id": f"gmail_msg_{datetime.now().timestamp()}",
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending via Gmail API: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _log_email_send(self, response: GeneratedResponse, send_result: Dict[str, Any], session: AsyncSession) -> None:
        """Log the email send for analytics and auditing"""
        try:
            # This would log to a dedicated audit table
            # For now, just log to application logs
            
            log_data = {
                "response_id": str(response.id),
                "user_id": response.user_id,
                "original_email_id": response.original_email_id,
                "gmail_message_id": send_result.get("message_id"),
                "sent_at": send_result.get("sent_at"),
                "confidence_score": response.confidence_score,
                "auto_sent": True
            }
            
            logger.info(f"Email send logged: {log_data}")
            
        except Exception as e:
            logger.error(f"Error logging email send: {str(e)}")
    
    async def generate_daily_summary_email(self, user_id: str) -> Dict[str, Any]:
        """Generate daily summary email for a user"""
        try:
            async with AsyncSessionLocal() as session:
                yesterday = datetime.now().date() - timedelta(days=1)
                
                # Get emails sent yesterday
                sent_stmt = select(GeneratedResponse).where(
                    and_(
                        GeneratedResponse.user_id == user_id,
                        GeneratedResponse.status == "sent",
                        func.date(GeneratedResponse.sent_at) == yesterday
                    )
                )
                sent_result = await session.execute(sent_stmt)
                sent_responses = sent_result.scalars().all()
                
                # Get emails received yesterday
                received_stmt = select(EmailMessage).where(
                    and_(
                        EmailMessage.user_id == user_id,
                        EmailMessage.direction == "incoming",
                        func.date(EmailMessage.timestamp) == yesterday
                    )
                )
                received_result = await session.execute(received_stmt)
                received_emails = received_result.scalars().all()
                
                # Generate summary
                summary = {
                    "date": yesterday.isoformat(),
                    "user_id": user_id,
                    "emails_received": len(received_emails),
                    "auto_responses_sent": len([r for r in sent_responses if r.is_auto_generated]),
                    "manual_responses_sent": len([r for r in sent_responses if not r.is_auto_generated]),
                    "total_responses": len(sent_responses),
                    "avg_confidence_score": sum(r.confidence_score for r in sent_responses) / len(sent_responses) if sent_responses else 0,
                    "response_rate": len(sent_responses) / max(len(received_emails), 1),
                    "generated_at": datetime.now().isoformat()
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error generating daily summary for user {user_id}: {str(e)}")
            raise
    
    async def send_daily_summary_email(self, user_id: str) -> bool:
        """Send daily summary email to user"""
        try:
            # Generate summary
            summary = await self.generate_daily_summary_email(user_id)
            
            # Get user info
            async with AsyncSessionLocal() as session:
                user = await self._get_user(user_id, session)
                if not user:
                    return False
                
                # Prepare summary email content
                email_content = self._prepare_daily_summary_content(summary, user)
                
                # Send summary email
                send_result = await self._send_via_gmail_api(
                    user_id=user_id,
                    email_content=email_content,
                    original_email=None  # This is an original email, not a reply
                )
                
                if send_result["success"]:
                    logger.info(f"Daily summary email sent to user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to send daily summary email: {send_result.get('error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending daily summary email to user {user_id}: {str(e)}")
            return False
    
    def _prepare_daily_summary_content(self, summary: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Prepare daily summary email content"""
        date_str = summary["date"]
        
        subject = f"AI Email Assistant - Denní přehled {date_str}"
        
        body = f"""Dobrý den {user.display_name or 'Uživateli'},

zde je váš denní přehled e-mailové aktivity za {date_str}:

📨 E-maily:
• Přijaté e-maily: {summary['emails_received']}
• Automatické odpovědi: {summary['auto_responses_sent']}
• Manuální odpovědi: {summary['manual_responses_sent']}
• Celkem odpovědí: {summary['total_responses']}

📊 Statistiky:
• Rychlost odpovědí: {summary['response_rate']:.1%}
• Průměrná spolehlivost: {summary['avg_confidence_score']:.1%}

🤖 AI Email Assistant pokračuje v monitorování vašich e-mailů každou minutu a generuje kontextové odpovědi na základě vašeho stylu komunikace.

Přejeme krásný den!

--
AI Email Assistant
Automaticky generováno {summary['generated_at']}
"""
        
        return {
            "to": user.email,
            "subject": subject,
            "body": body,
            "thread_id": None
        }


# Global instance
auto_send_service = AutoSendService()