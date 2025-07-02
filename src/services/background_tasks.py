"""
Background Task Processing Service

This module provides background task processing capabilities using Celery
for asynchronous email analysis, response generation, and data processing.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy import select, and_

from src.config.settings import settings
from src.config.database import AsyncSessionLocal
from src.models.email import EmailMessage
from src.models.client import Client
from src.models.response import GeneratedResponse, WritingStyleProfile
from src.services.email_analyzer import EmailAnalysisEngine
from src.services.response_generator import ResponseGeneratorService
from src.services.vector_db_manager import VectorDatabaseManager
from src.services.rag_engine import RAGEngine
from src.services.client_analyzer import ClientRelationshipAnalyzer
from src.services.style_analyzer import WritingStyleAnalyzer
from src.services.topic_analyzer import TopicAnalyzer
from src.services.rule_generator import RuleGeneratorService

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    'ai_email_assistant',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['src.services.background_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

class BackgroundTaskManager:
    """Manager for background task operations"""
    
    def __init__(self):
        self.celery_app = celery_app
        
    async def submit_email_analysis(self, email_id: str, user_id: str, priority: str = "normal") -> str:
        """Submit email for background analysis"""
        try:
            task = analyze_email_task.delay(email_id, user_id)
            logger.info(f"Submitted email {email_id} for analysis, task ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit email analysis task: {e}")
            raise
    
    async def submit_batch_analysis(self, email_ids: List[str], user_id: str) -> str:
        """Submit batch of emails for analysis"""
        try:
            task = analyze_email_batch_task.delay(email_ids, user_id)
            logger.info(f"Submitted {len(email_ids)} emails for batch analysis, task ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit batch analysis task: {e}")
            raise
    
    async def submit_response_generation(self, email_id: str, user_id: str, options: Optional[Dict] = None) -> str:
        """Submit email for response generation"""
        try:
            task = generate_response_task.delay(email_id, user_id, options or {})
            logger.info(f"Submitted email {email_id} for response generation, task ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit response generation task: {e}")
            raise
    
    async def submit_vectorization(self, email_ids: List[str], user_id: str) -> str:
        """Submit emails for vectorization"""
        try:
            task = vectorize_emails_task.delay(email_ids, user_id)
            logger.info(f"Submitted {len(email_ids)} emails for vectorization, task ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit vectorization task: {e}")
            raise
    
    async def submit_user_profile_update(self, user_id: str) -> str:
        """Submit user profile update task"""
        try:
            task = update_user_profile_task.delay(user_id)
            logger.info(f"Submitted user profile update for {user_id}, task ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit user profile update task: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and result"""
        try:
            result = AsyncResult(task_id, app=celery_app)
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result,
                "traceback": result.traceback,
                "date_done": result.date_done,
                "successful": result.successful()
            }
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": str(e)
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a background task"""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

# Initialize task manager
task_manager = BackgroundTaskManager()

@celery_app.task(bind=True, name='analyze_email_task')
def analyze_email_task(self, email_id: str, user_id: str) -> Dict[str, Any]:
    """Background task for analyzing a single email"""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Starting email analysis'})
        
        # Run async analysis in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_analyze_email_async(email_id, user_id, self))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Email analysis task failed for {email_id}: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='analyze_email_batch_task')
def analyze_email_batch_task(self, email_ids: List[str], user_id: str) -> Dict[str, Any]:
    """Background task for analyzing a batch of emails"""
    try:
        self.update_state(state='PROGRESS', meta={'status': f'Starting batch analysis of {len(email_ids)} emails'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_analyze_email_batch_async(email_ids, user_id, self))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Batch analysis task failed: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='generate_response_task')
def generate_response_task(self, email_id: str, user_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Background task for generating email response"""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Starting response generation'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_generate_response_async(email_id, user_id, options, self))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Response generation task failed for {email_id}: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='vectorize_emails_task')
def vectorize_emails_task(self, email_ids: List[str], user_id: str) -> Dict[str, Any]:
    """Background task for vectorizing emails"""
    try:
        self.update_state(state='PROGRESS', meta={'status': f'Starting vectorization of {len(email_ids)} emails'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_vectorize_emails_async(email_ids, user_id, self))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Vectorization task failed: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='update_user_profile_task')
def update_user_profile_task(self, user_id: str) -> Dict[str, Any]:
    """Background task for updating user profile"""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Starting user profile update'})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_update_user_profile_async(user_id, self))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"User profile update task failed for {user_id}: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(name='cleanup_old_tasks')
def cleanup_old_tasks() -> Dict[str, Any]:
    """Periodic task to cleanup old completed tasks"""
    try:
        # This would integrate with Celery's result backend cleanup
        # For now, we'll just log the cleanup attempt
        logger.info("Running periodic task cleanup")
        
        return {
            "status": "success",
            "message": "Task cleanup completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Task cleanup failed: {e}")
        raise

@celery_app.task(name='generate_daily_analytics')
def generate_daily_analytics() -> Dict[str, Any]:
    """Periodic task to generate daily analytics"""
    try:
        logger.info("Generating daily analytics")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_generate_daily_analytics_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Daily analytics generation failed: {e}")
        raise

@celery_app.task(name='monitor_all_user_emails')
def monitor_all_user_emails() -> Dict[str, Any]:
    """Periodic task to monitor emails for all users every minute"""
    try:
        logger.info("Starting minute-by-minute email monitoring for all users")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_monitor_all_user_emails_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Email monitoring failed: {e}")
        raise

@celery_app.task(name='generate_daily_summaries')
def generate_daily_summaries() -> Dict[str, Any]:
    """Periodic task to generate daily summaries for all users"""
    try:
        logger.info("Generating daily summaries for all users")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_generate_daily_summaries_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Daily summaries generation failed: {e}")
        raise

@celery_app.task(name='process_auto_send_queue')
def process_auto_send_queue() -> Dict[str, Any]:
    """Periodic task to process auto-send email queue"""
    try:
        logger.info("Processing auto-send email queue")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_process_auto_send_queue_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Auto-send queue processing failed: {e}")
        raise

@celery_app.task(name='send_daily_summary_emails')
def send_daily_summary_emails() -> Dict[str, Any]:
    """Periodic task to send daily summary emails to users"""
    try:
        logger.info("Sending daily summary emails")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_send_daily_summary_emails_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Daily summary email sending failed: {e}")
        raise

# Async task implementations

async def _analyze_email_async(email_id: str, user_id: str, task) -> Dict[str, Any]:
    """Async implementation of email analysis"""
    try:
        async with AsyncSessionLocal() as session:
            # Get email
            stmt = select(EmailMessage).where(EmailMessage.id == email_id)
            result = await session.execute(stmt)
            email = result.scalar_one_or_none()
            
            if not email:
                raise ValueError(f"Email {email_id} not found")
            
            task.update_state(state='PROGRESS', meta={'status': 'Email retrieved, starting analysis'})
            
            # Initialize analyzers
            client_analyzer = ClientRelationshipAnalyzer()
            style_analyzer = WritingStyleAnalyzer()
            topic_analyzer = TopicAnalyzer()
            email_analyzer = EmailAnalysisEngine(client_analyzer, style_analyzer, topic_analyzer)
            
            # Perform analysis
            analysis_result = await email_analyzer.analyze_email(email, user_id)
            
            task.update_state(state='PROGRESS', meta={'status': 'Analysis complete, updating database'})
            
            # Update email with analysis results
            email.is_analyzed = True
            email.analyzed_at = datetime.utcnow()
            email.analysis_results = analysis_result
            
            await session.commit()
            
            return {
                "status": "success",
                "email_id": email_id,
                "analysis_result": analysis_result,
                "processed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in email analysis: {e}")
        raise

async def _analyze_email_batch_async(email_ids: List[str], user_id: str, task) -> Dict[str, Any]:
    """Async implementation of batch email analysis"""
    try:
        async with AsyncSessionLocal() as session:
            # Get emails
            stmt = select(EmailMessage).where(EmailMessage.id.in_(email_ids))
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            if not emails:
                raise ValueError("No emails found for analysis")
            
            # Initialize analyzers
            client_analyzer = ClientRelationshipAnalyzer()
            style_analyzer = WritingStyleAnalyzer()
            topic_analyzer = TopicAnalyzer()
            email_analyzer = EmailAnalysisEngine(client_analyzer, style_analyzer, topic_analyzer)
            
            # Analyze emails in batch
            batch_result = await email_analyzer.analyze_email_batch(emails, user_id)
            
            task.update_state(state='PROGRESS', meta={'status': 'Batch analysis complete, updating database'})
            
            # Update emails with results
            for email in emails:
                email.is_analyzed = True
                email.analyzed_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "status": "success",
                "processed_count": len(emails),
                "batch_result": batch_result,
                "processed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in batch email analysis: {e}")
        raise

async def _generate_response_async(email_id: str, user_id: str, options: Dict[str, Any], task) -> Dict[str, Any]:
    """Async implementation of response generation"""
    try:
        async with AsyncSessionLocal() as session:
            # Get email
            stmt = select(EmailMessage).where(EmailMessage.id == email_id)
            result = await session.execute(stmt)
            email = result.scalar_one_or_none()
            
            if not email:
                raise ValueError(f"Email {email_id} not found")
            
            task.update_state(state='PROGRESS', meta={'status': 'Email retrieved, initializing generators'})
            
            # Initialize services
            vector_manager = VectorDatabaseManager()
            await vector_manager.initialize_collections()
            
            rag_engine = RAGEngine(vector_manager)
            rule_generator = RuleGeneratorService()
            style_analyzer = WritingStyleAnalyzer()
            
            response_generator = ResponseGeneratorService(
                rag_engine=rag_engine,
                rule_generator=rule_generator,
                style_analyzer=style_analyzer
            )
            
            task.update_state(state='PROGRESS', meta={'status': 'Generating response'})
            
            # Generate response
            response_result = await response_generator.generate_response(
                incoming_email=email,
                user_id=user_id,
                generation_options=options
            )
            
            return {
                "status": "success",
                "email_id": email_id,
                "response_result": {
                    "response_text": response_result.response_text,
                    "response_type": response_result.response_type,
                    "confidence_score": response_result.confidence_score,
                    "generation_time_ms": response_result.generation_time_ms
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in response generation: {e}")
        raise

async def _vectorize_emails_async(email_ids: List[str], user_id: str, task) -> Dict[str, Any]:
    """Async implementation of email vectorization"""
    try:
        async with AsyncSessionLocal() as session:
            # Get emails
            stmt = select(EmailMessage).where(EmailMessage.id.in_(email_ids))
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            if not emails:
                raise ValueError("No emails found for vectorization")
            
            task.update_state(state='PROGRESS', meta={'status': 'Emails retrieved, starting vectorization'})
            
            # Initialize vector manager
            vector_manager = VectorDatabaseManager()
            await vector_manager.initialize_collections()
            
            # Vectorize emails
            vectorization_result = await vector_manager.chunk_and_embed_emails(emails, user_id)
            
            task.update_state(state='PROGRESS', meta={'status': 'Storing vectors'})
            
            # Store vectors
            for collection_name, chunks in vectorization_result.items():
                if chunks:
                    await vector_manager.store_email_chunks(collection_name, chunks)
            
            return {
                "status": "success",
                "processed_count": len(emails),
                "collections_updated": list(vectorization_result.keys()),
                "total_chunks": sum(len(chunks) for chunks in vectorization_result.values()),
                "vectorized_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in email vectorization: {e}")
        raise

async def _update_user_profile_async(user_id: str, task) -> Dict[str, Any]:
    """Async implementation of user profile update"""
    try:
        async with AsyncSessionLocal() as session:
            task.update_state(state='PROGRESS', meta={'status': 'Analyzing user communication patterns'})
            
            # Get user's emails for analysis
            stmt = select(EmailMessage).where(
                and_(
                    EmailMessage.user_id == user_id,
                    EmailMessage.analyzed_at.isnot(None)
                )
            ).limit(100)
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            if not emails:
                return {
                    "status": "success",
                    "message": "No analyzed emails found for profile update",
                    "user_id": user_id
                }
            
            # Initialize analyzers
            style_analyzer = WritingStyleAnalyzer()
            
            # Analyze writing style
            style_result = await style_analyzer.analyze_writing_style(user_id, emails)
            
            task.update_state(state='PROGRESS', meta={'status': 'Updating user profile'})
            
            # Update or create writing style profile
            stmt = select(WritingStyleProfile).where(WritingStyleProfile.user_id == user_id)
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            
            if profile:
                # Update existing profile
                profile.formality_score = style_result.get('formality_score', profile.formality_score)
                profile.common_phrases = style_result.get('common_phrases', profile.common_phrases)
                profile.closing_patterns = style_result.get('closing_patterns', profile.closing_patterns)
                profile.confidence_score = style_result.get('confidence_score', profile.confidence_score)
                profile.updated_at = datetime.utcnow()
            else:
                # Create new profile
                profile = WritingStyleProfile(
                    user_id=user_id,
                    formality_score=style_result.get('formality_score', 0.7),
                    common_phrases=style_result.get('common_phrases', []),
                    closing_patterns=style_result.get('closing_patterns', []),
                    confidence_score=style_result.get('confidence_score', 0.5)
                )
                session.add(profile)
            
            await session.commit()
            
            return {
                "status": "success",
                "user_id": user_id,
                "profile_updated": True,
                "emails_analyzed": len(emails),
                "updated_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in user profile update: {e}")
        raise

async def _generate_daily_analytics_async() -> Dict[str, Any]:
    """Async implementation of daily analytics generation"""
    try:
        async with AsyncSessionLocal() as session:
            # Calculate analytics for the last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Count emails processed
            email_stmt = select(EmailMessage).where(EmailMessage.created_at >= yesterday)
            email_result = await session.execute(email_stmt)
            emails_processed = len(email_result.scalars().all())
            
            # Count responses generated
            response_stmt = select(GeneratedResponse).where(GeneratedResponse.created_at >= yesterday)
            response_result = await session.execute(response_stmt)
            responses_generated = len(response_result.scalars().all())
            
            analytics = {
                "date": yesterday.date().isoformat(),
                "emails_processed": emails_processed,
                "responses_generated": responses_generated,
                "processing_rate": responses_generated / max(emails_processed, 1),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Daily analytics generated: {analytics}")
            
            return {
                "status": "success",
                "analytics": analytics
            }
            
    except Exception as e:
        logger.error(f"Error in daily analytics generation: {e}")
        raise

async def _monitor_all_user_emails_async() -> Dict[str, Any]:
    """Async implementation of email monitoring for all users"""
    try:
        from src.services.email_monitoring_service import email_monitoring_service
        
        # Monitor emails for all users
        result = await email_monitoring_service.monitor_all_users()
        
        logger.info(f"Email monitoring completed: {result}")
        
        return {
            "status": "success",
            "monitoring_result": result
        }
        
    except Exception as e:
        logger.error(f"Error in email monitoring: {e}")
        raise

async def _generate_daily_summaries_async() -> Dict[str, Any]:
    """Async implementation of daily summaries generation"""
    try:
        from src.services.email_monitoring_service import email_monitoring_service
        from src.models.user import User
        
        async with AsyncSessionLocal() as session:
            # Get all active users
            stmt = select(User).where(User.is_active == True)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            summaries_generated = 0
            
            for user in users:
                try:
                    # Check if user has automation enabled for daily summaries
                    from src.models.setup_wizard import AutomationConfiguration
                    
                    auto_stmt = select(AutomationConfiguration).where(
                        AutomationConfiguration.user_id == user.id
                    )
                    auto_result = await session.execute(auto_stmt)
                    automation_config = auto_result.scalar_one_or_none()
                    
                    if automation_config and automation_config.daily_summary_enabled:
                        summary = await email_monitoring_service.generate_daily_summary(str(user.id))
                        
                        # Here you would send the summary via email or notification
                        # For now, we'll just log it
                        logger.info(f"Daily summary generated for user {user.id}: {summary}")
                        summaries_generated += 1
                        
                except Exception as e:
                    logger.error(f"Error generating daily summary for user {user.id}: {str(e)}")
            
            return {
                "status": "success",
                "summaries_generated": summaries_generated,
                "total_users": len(users),
                "generated_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in daily summaries generation: {e}")
        raise

async def _process_auto_send_queue_async() -> Dict[str, Any]:
    """Async implementation of auto-send queue processing"""
    try:
        from src.services.auto_send_service import auto_send_service
        
        # Process the auto-send queue
        result = await auto_send_service.process_auto_send_queue()
        
        logger.info(f"Auto-send queue processing completed: {result}")
        
        return {
            "status": "success",
            "processing_result": result
        }
        
    except Exception as e:
        logger.error(f"Error in auto-send queue processing: {e}")
        raise

async def _send_daily_summary_emails_async() -> Dict[str, Any]:
    """Async implementation of daily summary email sending"""
    try:
        from src.services.auto_send_service import auto_send_service
        from src.models.user import User
        
        async with AsyncSessionLocal() as session:
            # Get all active users with daily summary enabled
            from src.models.setup_wizard import AutomationConfiguration
            
            stmt = select(User).join(AutomationConfiguration).where(
                and_(
                    User.is_active == True,
                    AutomationConfiguration.daily_summary_enabled == True
                )
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            summaries_sent = 0
            errors = []
            
            for user in users:
                try:
                    # Check if it's time to send daily summary
                    automation_stmt = select(AutomationConfiguration).where(
                        AutomationConfiguration.user_id == user.id
                    )
                    automation_result = await session.execute(automation_stmt)
                    automation_config = automation_result.scalar_one_or_none()
                    
                    if automation_config and await _should_send_daily_summary(user.id, automation_config):
                        success = await auto_send_service.send_daily_summary_email(str(user.id))
                        
                        if success:
                            summaries_sent += 1
                            logger.info(f"Daily summary sent to user {user.id}")
                        else:
                            errors.append(f"Failed to send daily summary to user {user.id}")
                            
                except Exception as e:
                    error_msg = f"Error sending daily summary to user {user.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                "status": "success",
                "summaries_sent": summaries_sent,
                "total_eligible_users": len(users),
                "errors": errors,
                "processed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in daily summary email sending: {e}")
        raise

async def _should_send_daily_summary(user_id: str, automation_config: AutomationConfiguration) -> bool:
    """Check if it's time to send daily summary for user"""
    try:
        # Check if it's the right time based on user's daily_summary_time setting
        from datetime import datetime, time
        
        now = datetime.now()
        summary_time = datetime.strptime(automation_config.daily_summary_time, '%H:%M').time()
        
        # Check if current time is within 1 hour of the configured summary time
        current_time = now.time()
        
        # Simple check: if we're within the hour of the summary time
        summary_hour = summary_time.hour
        current_hour = current_time.hour
        
        # Send if we're in the right hour and haven't sent today yet
        if current_hour == summary_hour:
            # Additional check could be added to ensure we don't send multiple times per day
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking daily summary timing: {e}")
        return False

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'monitor-emails-every-minute': {
        'task': 'monitor_all_user_emails',
        'schedule': 60.0,  # Every minute - Ultimate AI Email Agent requirement
    },
    'process-auto-send-queue': {
        'task': 'process_auto_send_queue',
        'schedule': 120.0,  # Every 2 minutes - Auto-send processing
    },
    'send-daily-summaries': {
        'task': 'send_daily_summary_emails',
        'schedule': 21600.0,  # Every 6 hours - Check for daily summaries to send
    },
    'cleanup-old-tasks': {
        'task': 'cleanup_old_tasks',
        'schedule': 3600.0,  # Every hour
    },
    'generate-daily-analytics': {
        'task': 'generate_daily_analytics',
        'schedule': 86400.0,  # Every day
    },
    'generate-daily-summaries': {
        'task': 'generate_daily_summaries',
        'schedule': 28800.0,  # Every 8 hours (3 times per day)
    },
}

celery_app.conf.timezone = 'UTC'