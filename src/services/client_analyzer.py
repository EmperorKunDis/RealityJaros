from collections import defaultdict, Counter
from typing import Dict, List, Set, Optional, Tuple
import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.models.email import EmailMessage
from src.models.client import Client
from src.config.database import AsyncSessionLocal
from src.utils.email_parsing import EmailParser

logger = logging.getLogger(__name__)

@dataclass
class ClientProfile:
    """Comprehensive client profile data"""
    email_address: str
    domain: str
    client_name: Optional[str]
    organization_name: Optional[str]
    total_emails_received: int
    total_emails_sent: int
    first_interaction: datetime
    last_interaction: datetime
    communication_frequency: str
    avg_response_time_hours: float
    business_category: str
    industry_sector: str
    formality_level: str
    common_topics: List[str]
    frequent_questions: List[str]
    project_keywords: List[str]

class ClientAnalyzer:
    """
    Sophisticated client categorization and relationship mapping
    Analyzes email patterns to identify client relationships
    """
    
    def __init__(self):
        self.email_parser = EmailParser()
        self.business_domains = self._load_business_domain_patterns()
        self.industry_keywords = self._load_industry_keywords()
        
    async def analyze_client_relationships(self, user_id: str) -> Dict[str, ClientProfile]:
        """
        Analyze email patterns to identify client relationships
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary mapping email addresses to client profiles
        """
        try:
            logger.info(f"Starting client relationship analysis for user {user_id}")
            
            async with AsyncSessionLocal() as session:
                # Get all emails for user
                emails = await self._get_user_emails(user_id, session)
                
                if not emails:
                    logger.info("No emails found for analysis")
                    return {}
                
                # Group emails by sender/recipient
                client_emails = self._group_emails_by_client(emails, user_id)
                
                # Analyze each client relationship
                client_profiles = {}
                for email_address, email_list in client_emails.items():
                    try:
                        profile = await self._analyze_individual_client(email_address, email_list)
                        client_profiles[email_address] = profile
                        
                        # Create or update client record in database
                        await self._create_or_update_client(user_id, profile, session)
                        
                    except Exception as e:
                        logger.error(f"Error analyzing client {email_address}: {e}")
                        continue
                
                await session.commit()
                
                logger.info(f"Analyzed {len(client_profiles)} client relationships")
                return client_profiles
                
        except Exception as e:
            logger.error(f"Error in analyze_client_relationships: {e}")
            return {}

    async def _get_user_emails(self, user_id: str, session) -> List[EmailMessage]:
        """
        Get all emails for a user from database
        
        Args:
            user_id: User identifier
            session: Database session
            
        Returns:
            List of EmailMessage objects
        """
        try:
            from sqlalchemy import select
            
            stmt = select(EmailMessage).where(
                EmailMessage.user_id == user_id,
                EmailMessage.is_processed == True  # Only processed emails
            ).order_by(EmailMessage.sent_datetime.desc())
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            return list(emails)
            
        except Exception as e:
            logger.error(f"Error fetching user emails: {e}")
            return []

    def _group_emails_by_client(self, emails: List[EmailMessage], user_id: str) -> Dict[str, List[EmailMessage]]:
        """
        Group emails by client email address
        
        Args:
            emails: List of email messages
            user_id: User identifier for determining direction
            
        Returns:
            Dictionary mapping client email addresses to their emails
        """
        client_emails = defaultdict(list)
        
        try:
            for email in emails:
                # Determine the client email address based on direction
                if email.direction == 'incoming':
                    # For incoming emails, client is the sender
                    client_email = self._extract_clean_email(email.sender)
                else:
                    # For outgoing emails, client is the recipient
                    client_email = self._extract_clean_email(email.recipient)
                
                if client_email and self._is_valid_client_email(client_email):
                    client_emails[client_email].append(email)
            
            # Filter out clients with very few emails (likely not real clients)
            filtered_clients = {
                email: emails for email, emails in client_emails.items()
                if len(emails) >= 2  # At least 2 emails to be considered a client
            }
            
            return filtered_clients
            
        except Exception as e:
            logger.error(f"Error grouping emails by client: {e}")
            return {}

    def _extract_clean_email(self, email_string: str) -> Optional[str]:
        """
        Extract clean email address from email string
        
        Args:
            email_string: Email string potentially with name
            
        Returns:
            Clean email address
        """
        try:
            if not email_string:
                return None
            
            # Extract email from "Name <email@domain.com>" format
            email_match = re.search(r'<([^>]+)>', email_string)
            if email_match:
                return email_match.group(1).strip().lower()
            
            # Check if it's already a clean email
            if '@' in email_string:
                return email_string.strip().lower()
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting email from '{email_string}': {e}")
            return None

    def _is_valid_client_email(self, email: str) -> bool:
        """
        Check if email address represents a valid client
        
        Args:
            email: Email address
            
        Returns:
            True if valid client email
        """
        try:
            # Basic email validation
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                return False
            
            # Filter out common non-client domains
            excluded_domains = {
                'noreply', 'no-reply', 'donotreply', 'notifications',
                'support', 'admin', 'system', 'automated'
            }
            
            domain = email.split('@')[1].lower()
            local_part = email.split('@')[0].lower()
            
            # Check for excluded patterns
            for excluded in excluded_domains:
                if excluded in local_part or excluded in domain:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating client email '{email}': {e}")
            return False

    async def _analyze_individual_client(self, email_address: str, emails: List[EmailMessage]) -> ClientProfile:
        """
        Analyze individual client based on their emails
        
        Args:
            email_address: Client email address
            emails: List of emails with this client
            
        Returns:
            Client profile
        """
        try:
            # Basic statistics
            total_emails = len(emails)
            incoming_emails = [e for e in emails if e.direction == 'incoming']
            outgoing_emails = [e for e in emails if e.direction == 'outgoing']
            
            # Timeline analysis
            sorted_emails = sorted(emails, key=lambda x: x.sent_datetime)
            first_interaction = sorted_emails[0].sent_datetime
            last_interaction = sorted_emails[-1].sent_datetime
            
            # Communication frequency
            comm_frequency = self._calculate_communication_frequency(emails)
            
            # Response time analysis
            avg_response_time = self._calculate_avg_response_time(emails)
            
            # Extract names and organization
            client_name, org_name = self._extract_client_names(emails)
            
            # Domain analysis
            domain = email_address.split('@')[1]
            
            # Business categorization
            business_category = self._categorize_business_type(emails, domain)
            industry_sector = self._identify_industry_sector(emails, domain)
            
            # Communication style analysis
            formality_level = self._analyze_formality_level(emails)
            
            # Content analysis
            common_topics = self._extract_common_topics(emails)
            frequent_questions = self._extract_frequent_questions(emails)
            project_keywords = self._extract_project_keywords(emails)
            
            return ClientProfile(
                email_address=email_address,
                domain=domain,
                client_name=client_name,
                organization_name=org_name,
                total_emails_received=len(incoming_emails),
                total_emails_sent=len(outgoing_emails),
                first_interaction=first_interaction,
                last_interaction=last_interaction,
                communication_frequency=comm_frequency,
                avg_response_time_hours=avg_response_time,
                business_category=business_category,
                industry_sector=industry_sector,
                formality_level=formality_level,
                common_topics=common_topics,
                frequent_questions=frequent_questions,
                project_keywords=project_keywords
            )
            
        except Exception as e:
            logger.error(f"Error analyzing client {email_address}: {e}")
            raise

    def _calculate_communication_frequency(self, emails: List[EmailMessage]) -> str:
        """
        Calculate communication frequency based on email timestamps
        
        Args:
            emails: List of email messages
            
        Returns:
            Frequency category: daily, weekly, monthly, rare
        """
        try:
            if len(emails) < 2:
                return "rare"
            
            sorted_emails = sorted(emails, key=lambda x: x.sent_datetime)
            
            # Calculate average time between emails
            total_days = (sorted_emails[-1].sent_datetime - sorted_emails[0].sent_datetime).days
            if total_days == 0:
                return "daily"
            
            avg_days_between = total_days / (len(emails) - 1)
            
            if avg_days_between <= 1:
                return "daily"
            elif avg_days_between <= 7:
                return "weekly"
            elif avg_days_between <= 30:
                return "monthly"
            else:
                return "rare"
                
        except Exception as e:
            logger.warning(f"Error calculating communication frequency: {e}")
            return "rare"

    def _calculate_avg_response_time(self, emails: List[EmailMessage]) -> float:
        """
        Calculate average response time in hours
        
        Args:
            emails: List of email messages
            
        Returns:
            Average response time in hours
        """
        try:
            # Group emails by thread
            threads = defaultdict(list)
            for email in emails:
                threads[email.thread_id].append(email)
            
            response_times = []
            
            for thread_emails in threads.values():
                if len(thread_emails) < 2:
                    continue
                
                # Sort by time
                sorted_thread = sorted(thread_emails, key=lambda x: x.sent_datetime)
                
                # Find response pairs (incoming followed by outgoing)
                for i in range(len(sorted_thread) - 1):
                    current = sorted_thread[i]
                    next_email = sorted_thread[i + 1]
                    
                    if (current.direction == 'incoming' and 
                        next_email.direction == 'outgoing'):
                        time_diff = next_email.sent_datetime - current.sent_datetime
                        response_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
            
            if response_times:
                return sum(response_times) / len(response_times)
            else:
                return 24.0  # Default 24 hours if no response pairs found
                
        except Exception as e:
            logger.warning(f"Error calculating response time: {e}")
            return 24.0

    def _extract_client_names(self, emails: List[EmailMessage]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract client name and organization from email signatures and headers
        
        Args:
            emails: List of email messages
            
        Returns:
            Tuple of (client_name, organization_name)
        """
        try:
            names = []
            organizations = []
            
            for email in emails:
                if email.direction == 'incoming' and email.sender:
                    # Extract name from sender field
                    sender_match = re.search(r'^([^<]+)<', email.sender)
                    if sender_match:
                        name = sender_match.group(1).strip().strip('"')
                        if name and len(name) > 1:
                            names.append(name)
                
                # Extract from signature in email body
                if email.body_text:
                    # Look for signature patterns
                    signature_patterns = [
                        r'Best regards,\s*([^\n]+)',
                        r'Sincerely,\s*([^\n]+)',
                        r'Thanks,\s*([^\n]+)',
                        r'Regards,\s*([^\n]+)',
                    ]
                    
                    for pattern in signature_patterns:
                        match = re.search(pattern, email.body_text, re.IGNORECASE)
                        if match:
                            name = match.group(1).strip()
                            if name and len(name) > 1:
                                names.append(name)
                    
                    # Look for organization mentions
                    org_patterns = [
                        r'([A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Ltd|Company|Co\.))\.?',
                        r'([A-Z][a-zA-Z\s&]+(?:Solutions|Services|Group|Partners))\.?',
                    ]
                    
                    for pattern in org_patterns:
                        matches = re.findall(pattern, email.body_text)
                        organizations.extend([match.strip() for match in matches])
            
            # Find most common name and organization
            client_name = None
            if names:
                name_counter = Counter(names)
                client_name = name_counter.most_common(1)[0][0]
            
            organization_name = None
            if organizations:
                org_counter = Counter(organizations)
                organization_name = org_counter.most_common(1)[0][0]
            
            return client_name, organization_name
            
        except Exception as e:
            logger.warning(f"Error extracting client names: {e}")
            return None, None

    def _categorize_business_type(self, emails: List[EmailMessage], domain: str) -> str:
        """
        Categorize business type based on email content and domain
        
        Args:
            emails: List of email messages
            domain: Email domain
            
        Returns:
            Business category
        """
        try:
            # Check domain patterns first
            for category, patterns in self.business_domains.items():
                if any(pattern in domain for pattern in patterns):
                    return category
            
            # Analyze email content
            all_text = ""
            for email in emails:
                if email.body_text:
                    all_text += email.body_text + " "
                if email.subject:
                    all_text += email.subject + " "
            
            all_text = all_text.lower()
            
            # Business category keywords
            categories = {
                'consulting': ['consulting', 'advisory', 'strategy', 'consulting'],
                'technology': ['software', 'development', 'api', 'code', 'technical'],
                'marketing': ['marketing', 'campaign', 'advertising', 'promotion'],
                'finance': ['finance', 'accounting', 'investment', 'financial'],
                'legal': ['legal', 'law', 'attorney', 'contract', 'agreement'],
                'healthcare': ['health', 'medical', 'doctor', 'clinic', 'hospital'],
                'education': ['education', 'school', 'university', 'training'],
                'retail': ['store', 'shop', 'product', 'sale', 'purchase'],
                'manufacturing': ['manufacturing', 'production', 'factory', 'industrial'],
                'real_estate': ['property', 'real estate', 'building', 'lease'],
            }
            
            for category, keywords in categories.items():
                if any(keyword in all_text for keyword in keywords):
                    return category
            
            return 'other'
            
        except Exception as e:
            logger.warning(f"Error categorizing business type: {e}")
            return 'other'

    def _identify_industry_sector(self, emails: List[EmailMessage], domain: str) -> str:
        """
        Identify industry sector based on email patterns
        
        Args:
            emails: List of email messages
            domain: Email domain
            
        Returns:
            Industry sector
        """
        try:
            # Simple implementation - can be expanded
            domain_lower = domain.lower()
            
            if any(word in domain_lower for word in ['tech', 'soft', 'dev', 'digital']):
                return 'technology'
            elif any(word in domain_lower for word in ['bank', 'finance', 'capital']):
                return 'financial_services'
            elif any(word in domain_lower for word in ['health', 'medical', 'pharma']):
                return 'healthcare'
            elif any(word in domain_lower for word in ['edu', 'school', 'university']):
                return 'education'
            elif any(word in domain_lower for word in ['gov', 'government']):
                return 'government'
            else:
                return 'general'
                
        except Exception as e:
            logger.warning(f"Error identifying industry sector: {e}")
            return 'general'

    def _analyze_formality_level(self, emails: List[EmailMessage]) -> str:
        """
        Analyze formality level of communication
        
        Args:
            emails: List of email messages
            
        Returns:
            Formality level: formal, semi-formal, casual
        """
        try:
            formal_indicators = ['dear sir', 'dear madam', 'yours sincerely', 'yours faithfully']
            casual_indicators = ['hey', 'hi there', 'thanks!', 'cheers', 'talk soon']
            
            formal_count = 0
            casual_count = 0
            
            for email in emails:
                if email.body_text:
                    text_lower = email.body_text.lower()
                    
                    formal_count += sum(1 for indicator in formal_indicators if indicator in text_lower)
                    casual_count += sum(1 for indicator in casual_indicators if indicator in text_lower)
            
            if formal_count > casual_count * 2:
                return 'formal'
            elif casual_count > formal_count * 2:
                return 'casual'
            else:
                return 'semi-formal'
                
        except Exception as e:
            logger.warning(f"Error analyzing formality level: {e}")
            return 'semi-formal'

    def _extract_common_topics(self, emails: List[EmailMessage]) -> List[str]:
        """Extract common topics from email content"""
        # Simplified implementation - return empty list for now
        # This would use more sophisticated NLP in a full implementation
        return []

    def _extract_frequent_questions(self, emails: List[EmailMessage]) -> List[str]:
        """Extract frequent questions from email content"""
        # Simplified implementation - return empty list for now
        return []

    def _extract_project_keywords(self, emails: List[EmailMessage]) -> List[str]:
        """Extract project-related keywords from email content"""
        # Simplified implementation - return empty list for now
        return []

    async def _create_or_update_client(self, user_id: str, profile: ClientProfile, session):
        """
        Create or update client record in database
        
        Args:
            user_id: User identifier
            profile: Client profile data
            session: Database session
        """
        try:
            from sqlalchemy import select
            
            # Check if client already exists
            stmt = select(Client).where(
                Client.user_id == user_id,
                Client.email_address == profile.email_address
            )
            result = await session.execute(stmt)
            client = result.scalar_one_or_none()
            
            if client:
                # Update existing client
                client.client_name = profile.client_name
                client.organization_name = profile.organization_name
                client.business_category = profile.business_category
                client.industry_sector = profile.industry_sector
                client.communication_frequency = profile.communication_frequency
                client.avg_response_time_hours = profile.avg_response_time_hours
                client.formality_level = profile.formality_level
                client.total_emails_received = profile.total_emails_received
                client.total_emails_sent = profile.total_emails_sent
                client.last_interaction = profile.last_interaction
                client.common_topics = profile.common_topics
                client.frequent_questions = profile.frequent_questions
                client.project_keywords = profile.project_keywords
                client.updated_at = datetime.utcnow()
                
                logger.info(f"Updated client: {profile.email_address}")
            else:
                # Create new client
                client = Client(
                    user_id=user_id,
                    email_address=profile.email_address,
                    email_domain=profile.domain,
                    client_name=profile.client_name,
                    organization_name=profile.organization_name,
                    business_category=profile.business_category,
                    industry_sector=profile.industry_sector,
                    communication_frequency=profile.communication_frequency,
                    avg_response_time_hours=profile.avg_response_time_hours,
                    formality_level=profile.formality_level,
                    total_emails_received=profile.total_emails_received,
                    total_emails_sent=profile.total_emails_sent,
                    first_interaction=profile.first_interaction,
                    last_interaction=profile.last_interaction,
                    common_topics=profile.common_topics,
                    frequent_questions=profile.frequent_questions,
                    project_keywords=profile.project_keywords
                )
                
                session.add(client)
                logger.info(f"Created new client: {profile.email_address}")
                
        except Exception as e:
            logger.error(f"Error creating/updating client {profile.email_address}: {e}")
            raise

    def _load_business_domain_patterns(self) -> Dict[str, List[str]]:
        """Load business domain classification patterns"""
        return {
            'consulting': ['consulting', 'advisory', 'strategy'],
            'technology': ['tech', 'software', 'digital', 'app', 'dev'],
            'finance': ['bank', 'finance', 'capital', 'invest'],
            'healthcare': ['health', 'medical', 'pharma', 'clinic'],
            'education': ['edu', 'school', 'university', 'academy'],
            'government': ['gov', 'government', 'public'],
            'legal': ['law', 'legal', 'attorney', 'counsel'],
            'marketing': ['marketing', 'advertis', 'agency', 'media'],
        }

    def _load_industry_keywords(self) -> Dict[str, List[str]]:
        """Load industry-specific keywords"""
        return {
            'technology': ['api', 'software', 'development', 'code', 'programming'],
            'finance': ['investment', 'portfolio', 'financial', 'banking', 'trading'],
            'healthcare': ['patient', 'treatment', 'medical', 'diagnosis', 'therapy'],
            'education': ['student', 'course', 'curriculum', 'learning', 'teaching'],
            'legal': ['contract', 'agreement', 'legal', 'law', 'litigation'],
            'marketing': ['campaign', 'brand', 'advertising', 'promotion', 'market'],
        }