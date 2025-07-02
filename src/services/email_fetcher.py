from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import asyncio
from googleapiclient.errors import HttpError

from src.services.auth_service import GoogleAuthenticationService
from src.utils.email_parsing import EmailParser
from src.models.email import EmailMessage, EmailChunk
from src.models.client import Client
from src.config.database import AsyncSessionLocal
from src.config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class EmailFetchResult:
    """Result of email fetching operation"""
    emails_fetched: int
    emails_processed: int
    new_emails: int
    errors: List[str]
    processing_time: float

class EmailFetcherService:
    """
    Advanced email fetching service with intelligent filtering
    Handles batch processing, rate limiting, and error recovery
    """
    
    def __init__(self, auth_service: GoogleAuthenticationService):
        self.auth_service = auth_service
        self.email_parser = EmailParser()
        self.batch_size = 100
        self.max_results_per_request = 500
        
    async def fetch_all_emails(self, user_id: str, credentials) -> EmailFetchResult:
        """
        Fetch complete email history with pagination
        
        Args:
            user_id: User identifier
            credentials: Google OAuth credentials
            
        Returns:
            Email fetch result summary
        """
        start_time = datetime.utcnow()
        emails_fetched = 0
        emails_processed = 0
        new_emails = 0
        errors = []
        
        try:
            gmail_service = await self.auth_service.get_gmail_service(credentials)
            
            # Get all message IDs first
            logger.info(f"Starting complete email fetch for user {user_id}")
            
            page_token = None
            all_message_ids = []
            
            while True:
                try:
                    # Fetch message list
                    request_params = {
                        'userId': 'me',
                        'maxResults': self.max_results_per_request,
                        'includeSpamTrash': False
                    }
                    
                    if page_token:
                        request_params['pageToken'] = page_token
                    
                    result = gmail_service.users().messages().list(**request_params).execute()
                    
                    messages = result.get('messages', [])
                    all_message_ids.extend([msg['id'] for msg in messages])
                    
                    page_token = result.get('nextPageToken')
                    if not page_token:
                        break
                        
                    logger.info(f"Fetched {len(all_message_ids)} message IDs so far...")
                    
                    # Add small delay to respect rate limits
                    await asyncio.sleep(0.1)
                    
                except HttpError as e:
                    error_msg = f"Error fetching message list: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    break
            
            logger.info(f"Found {len(all_message_ids)} total messages")
            
            # Process messages in batches
            async with AsyncSessionLocal() as session:
                for i in range(0, len(all_message_ids), self.batch_size):
                    batch_ids = all_message_ids[i:i + self.batch_size]
                    
                    try:
                        batch_result = await self._process_message_batch(
                            gmail_service, batch_ids, user_id, session
                        )
                        
                        emails_fetched += batch_result['fetched']
                        emails_processed += batch_result['processed'] 
                        new_emails += batch_result['new']
                        errors.extend(batch_result['errors'])
                        
                        # Commit batch
                        await session.commit()
                        
                        logger.info(f"Processed batch {i//self.batch_size + 1}/{(len(all_message_ids) + self.batch_size - 1)//self.batch_size}")
                        
                        # Rate limiting
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        error_msg = f"Error processing batch starting at {i}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        await session.rollback()
                        continue
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return EmailFetchResult(
                emails_fetched=emails_fetched,
                emails_processed=emails_processed,
                new_emails=new_emails,
                errors=errors,
                processing_time=processing_time
            )
            
        except Exception as e:
            error_msg = f"Critical error in fetch_all_emails: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return EmailFetchResult(
                emails_fetched=emails_fetched,
                emails_processed=emails_processed,
                new_emails=new_emails,
                errors=errors,
                processing_time=processing_time
            )

    async def fetch_new_emails(self, user_id: str, credentials, last_check: datetime) -> EmailFetchResult:
        """
        Fetch emails since last check timestamp
        
        Args:
            user_id: User identifier
            credentials: Google OAuth credentials
            last_check: Last synchronization timestamp
            
        Returns:
            Email fetch result summary
        """
        start_time = datetime.utcnow()
        emails_fetched = 0
        emails_processed = 0
        new_emails = 0
        errors = []
        
        try:
            gmail_service = await self.auth_service.get_gmail_service(credentials)
            
            # Convert datetime to Unix timestamp for Gmail query
            timestamp = int(last_check.timestamp())
            query = f"after:{timestamp}"
            
            logger.info(f"Fetching new emails for user {user_id} since {last_check}")
            
            # Search for messages newer than last check
            try:
                result = gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=self.max_results_per_request
                ).execute()
                
                messages = result.get('messages', [])
                message_ids = [msg['id'] for msg in messages]
                
                if not message_ids:
                    logger.info("No new emails found")
                    return EmailFetchResult(
                        emails_fetched=0,
                        emails_processed=0,
                        new_emails=0,
                        errors=[],
                        processing_time=(datetime.utcnow() - start_time).total_seconds()
                    )
                
                # Process new messages
                async with AsyncSessionLocal() as session:
                    batch_result = await self._process_message_batch(
                        gmail_service, message_ids, user_id, session
                    )
                    
                    emails_fetched = batch_result['fetched']
                    emails_processed = batch_result['processed']
                    new_emails = batch_result['new']
                    errors = batch_result['errors']
                    
                    await session.commit()
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                return EmailFetchResult(
                    emails_fetched=emails_fetched,
                    emails_processed=emails_processed,
                    new_emails=new_emails,
                    errors=errors,
                    processing_time=processing_time
                )
                
            except HttpError as e:
                error_msg = f"Error searching for new emails: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                
        except Exception as e:
            error_msg = f"Critical error in fetch_new_emails: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return EmailFetchResult(
            emails_fetched=emails_fetched,
            emails_processed=emails_processed,
            new_emails=new_emails,
            errors=errors,
            processing_time=processing_time
        )

    async def _process_message_batch(self, gmail_service, message_ids: List[str], user_id: str, session) -> Dict:
        """
        Process a batch of Gmail messages
        
        Args:
            gmail_service: Gmail API service instance
            message_ids: List of Gmail message IDs
            user_id: User identifier
            session: Database session
            
        Returns:
            Batch processing results
        """
        fetched = 0
        processed = 0
        new = 0
        errors = []
        
        try:
            # Check which messages already exist
            from sqlalchemy import select
            existing_stmt = select(EmailMessage.message_id).where(
                EmailMessage.user_id == user_id,
                EmailMessage.message_id.in_(message_ids)
            )
            result = await session.execute(existing_stmt)
            existing_ids = {row[0] for row in result.fetchall()}
            
            # Process only new messages
            new_message_ids = [mid for mid in message_ids if mid not in existing_ids]
            
            logger.info(f"Processing {len(new_message_ids)} new messages out of {len(message_ids)} total")
            
            for message_id in new_message_ids:
                try:
                    # Fetch full message
                    gmail_message = gmail_service.users().messages().get(
                        userId='me',
                        id=message_id,
                        format='full'
                    ).execute()
                    
                    fetched += 1
                    
                    # Parse message data
                    message_data = self.email_parser.extract_message_data(gmail_message)
                    
                    # Get user email for direction determination
                    user_email = await self._get_user_email(user_id, session)
                    if not user_email:
                        errors.append(f"Could not determine user email for message {message_id}")
                        continue
                    
                    # Determine email direction
                    direction = self.email_parser.determine_email_direction(
                        message_data['sender'],
                        message_data['recipient'],
                        user_email
                    )
                    
                    # Create email message record
                    email_message = EmailMessage(
                        user_id=user_id,
                        message_id=message_data['message_id'],
                        thread_id=message_data['thread_id'],
                        direction=direction,
                        subject=message_data['subject'],
                        sender=message_data['sender'],
                        recipient=message_data['recipient'],
                        cc_recipients=message_data.get('cc'),
                        bcc_recipients=message_data.get('bcc'),
                        body_text=message_data['body_text'],
                        body_html=message_data['body_html'],
                        snippet=message_data['snippet'],
                        labels=message_data['label_ids'],
                        has_attachments=message_data['has_attachments'],
                        attachment_count=len(message_data['attachments']),
                        sent_datetime=message_data['sent_datetime'] or datetime.utcnow(),
                        is_processed=False
                    )
                    
                    session.add(email_message)
                    processed += 1
                    new += 1
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.05)
                    
                except HttpError as e:
                    error_msg = f"Gmail API error for message {message_id}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                    
                except Exception as e:
                    error_msg = f"Error processing message {message_id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            return {
                'fetched': fetched,
                'processed': processed,
                'new': new,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Critical error in _process_message_batch: {e}"
            logger.error(error_msg)
            return {
                'fetched': fetched,
                'processed': processed,
                'new': new,
                'errors': errors + [error_msg]
            }

    async def _get_user_email(self, user_id: str, session) -> Optional[str]:
        """
        Get user's email address from database
        
        Args:
            user_id: User identifier
            session: Database session
            
        Returns:
            User's email address
        """
        try:
            from sqlalchemy import select
            from src.models.user import User
            
            stmt = select(User.email).where(User.id == user_id)
            result = await session.execute(stmt)
            user_email = result.scalar_one_or_none()
            
            return user_email
            
        except Exception as e:
            logger.error(f"Error getting user email: {e}")
            return None

    async def get_gmail_labels(self, credentials) -> List[Dict]:
        """
        Get available Gmail labels
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            List of Gmail labels
        """
        try:
            gmail_service = await self.auth_service.get_gmail_service(credentials)
            
            result = gmail_service.users().labels().list(userId='me').execute()
            labels = result.get('labels', [])
            
            return labels
            
        except Exception as e:
            logger.error(f"Error fetching Gmail labels: {e}")
            return []