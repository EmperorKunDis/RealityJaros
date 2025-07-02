from typing import List, Dict, Set, Tuple, Optional
import logging
from collections import Counter, defaultdict
import re
import math

from src.models.email import EmailMessage
from src.utils.text_processing import TextProcessor
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class TopicAnalyzer:
    """
    Advanced topic modeling and theme extraction
    Identifies common discussion topics and business categories
    """
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.business_keywords = self._load_business_keywords()
        self.topic_keywords = self._load_topic_keywords()
        
    async def extract_topics(self, user_id: str) -> Dict[str, List[str]]:
        """
        Extract dominant topics from email corpus
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary mapping topic categories to keywords
        """
        try:
            logger.info(f"Starting topic extraction for user {user_id}")
            
            async with AsyncSessionLocal() as session:
                # Get all processed emails
                emails = await self._get_user_emails(user_id, session)
                
                if not emails:
                    logger.info("No emails found for topic analysis")
                    return {}
                
                # Extract topics using multiple methods
                keyword_topics = self._extract_keyword_based_topics(emails)
                pattern_topics = self._extract_pattern_based_topics(emails)
                content_topics = self._extract_content_based_topics(emails)
                
                # Combine and rank topics
                combined_topics = self._combine_topic_results(
                    keyword_topics, pattern_topics, content_topics
                )
                
                logger.info(f"Extracted {len(combined_topics)} topic categories")
                return combined_topics
                
        except Exception as e:
            logger.error(f"Error in extract_topics: {e}")
            return {}

    async def categorize_business_types(self, user_id: str) -> Dict[str, str]:
        """
        Categorize clients by business type based on email content
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary mapping client emails to business categories
        """
        try:
            logger.info(f"Starting business type categorization for user {user_id}")
            
            async with AsyncSessionLocal() as session:
                # Get emails grouped by client
                client_emails = await self._get_emails_by_client(user_id, session)
                
                if not client_emails:
                    return {}
                
                business_categories = {}
                
                for client_email, emails in client_emails.items():
                    category = self._categorize_client_business(emails)
                    business_categories[client_email] = category
                
                logger.info(f"Categorized {len(business_categories)} clients")
                return business_categories
                
        except Exception as e:
            logger.error(f"Error in categorize_business_types: {e}")
            return {}

    async def identify_common_queries(self, user_id: str) -> List[str]:
        """
        Identify most frequent questions and requests
        
        Args:
            user_id: User identifier
            
        Returns:
            List of common questions/requests
        """
        try:
            logger.info(f"Starting common queries identification for user {user_id}")
            
            async with AsyncSessionLocal() as session:
                # Get incoming emails (queries to the user)
                incoming_emails = await self._get_incoming_emails(user_id, session)
                
                if not incoming_emails:
                    return []
                
                # Extract questions and requests
                questions = self._extract_questions(incoming_emails)
                requests = self._extract_requests(incoming_emails)
                
                # Combine and rank by frequency
                common_queries = self._rank_common_queries(questions + requests)
                
                logger.info(f"Identified {len(common_queries)} common queries")
                return common_queries[:20]  # Return top 20
                
        except Exception as e:
            logger.error(f"Error in identify_common_queries: {e}")
            return []

    async def _get_user_emails(self, user_id: str, session) -> List[EmailMessage]:
        """Get all user emails for analysis"""
        try:
            from sqlalchemy import select
            
            stmt = select(EmailMessage).where(
                EmailMessage.user_id == user_id,
                EmailMessage.body_text.isnot(None),
                EmailMessage.body_text != ''
            ).order_by(EmailMessage.sent_datetime.desc())
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            return list(emails)
            
        except Exception as e:
            logger.error(f"Error fetching user emails: {e}")
            return []

    async def _get_emails_by_client(self, user_id: str, session) -> Dict[str, List[EmailMessage]]:
        """Get emails grouped by client"""
        try:
            emails = await self._get_user_emails(user_id, session)
            
            client_emails = defaultdict(list)
            
            for email in emails:
                if email.direction == 'incoming':
                    client_email = self._extract_email_address(email.sender)
                else:
                    client_email = self._extract_email_address(email.recipient)
                
                if client_email:
                    client_emails[client_email].append(email)
            
            return dict(client_emails)
            
        except Exception as e:
            logger.error(f"Error grouping emails by client: {e}")
            return {}

    async def _get_incoming_emails(self, user_id: str, session) -> List[EmailMessage]:
        """Get incoming emails for query analysis"""
        try:
            from sqlalchemy import select
            
            stmt = select(EmailMessage).where(
                EmailMessage.user_id == user_id,
                EmailMessage.direction == 'incoming',
                EmailMessage.body_text.isnot(None),
                EmailMessage.body_text != ''
            ).order_by(EmailMessage.sent_datetime.desc()).limit(1000)
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            return list(emails)
            
        except Exception as e:
            logger.error(f"Error fetching incoming emails: {e}")
            return []

    def _extract_keyword_based_topics(self, emails: List[EmailMessage]) -> Dict[str, List[str]]:
        """Extract topics based on predefined keywords"""
        try:
            topic_scores = defaultdict(Counter)
            
            for email in emails:
                if not email.body_text:
                    continue
                
                text = email.body_text.lower()
                words = self.text_processor.extract_words(text, remove_stop_words=True)
                
                # Score topics based on keyword matches
                for topic, keywords in self.topic_keywords.items():
                    score = 0
                    for keyword in keywords:
                        if keyword in text:
                            score += text.count(keyword)
                    
                    if score > 0:
                        # Add top words from this email to this topic
                        email_words = Counter(words)
                        for word, count in email_words.most_common(10):
                            if len(word) > 3:  # Filter out very short words
                                topic_scores[topic][word] += count * score
            
            # Convert to final format
            result_topics = {}
            for topic, word_counts in topic_scores.items():
                if word_counts:
                    top_words = [word for word, count in word_counts.most_common(15)]
                    result_topics[topic] = top_words
            
            return result_topics
            
        except Exception as e:
            logger.error(f"Error extracting keyword-based topics: {e}")
            return {}

    def _extract_pattern_based_topics(self, emails: List[EmailMessage]) -> Dict[str, List[str]]:
        """Extract topics based on common patterns and phrases"""
        try:
            # Extract subjects and frequent phrases
            subjects = [email.subject for email in emails if email.subject]
            all_texts = [email.body_text for email in emails if email.body_text]
            
            # Analyze subjects for patterns
            subject_topics = self._analyze_subject_patterns(subjects)
            
            # Analyze frequent phrases
            phrase_topics = self._analyze_phrase_patterns(all_texts)
            
            # Combine results
            pattern_topics = {}
            pattern_topics.update(subject_topics)
            pattern_topics.update(phrase_topics)
            
            return pattern_topics
            
        except Exception as e:
            logger.error(f"Error extracting pattern-based topics: {e}")
            return {}

    def _extract_content_based_topics(self, emails: List[EmailMessage]) -> Dict[str, List[str]]:
        """Extract topics based on content analysis"""
        try:
            # Simple TF-IDF-like approach
            all_words = []
            email_word_sets = []
            
            for email in emails:
                if not email.body_text:
                    continue
                
                words = self.text_processor.extract_words(email.body_text, remove_stop_words=True)
                words = [w for w in words if len(w) > 3]  # Filter short words
                
                all_words.extend(words)
                email_word_sets.append(set(words))
            
            if not all_words:
                return {}
            
            # Calculate word importance scores
            word_scores = self._calculate_word_importance(all_words, email_word_sets)
            
            # Group important words into topics
            topics = self._cluster_words_into_topics(word_scores)
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting content-based topics: {e}")
            return {}

    def _analyze_subject_patterns(self, subjects: List[str]) -> Dict[str, List[str]]:
        """Analyze email subjects for topic patterns"""
        try:
            subject_words = []
            for subject in subjects:
                if subject:
                    words = self.text_processor.extract_words(subject, remove_stop_words=True)
                    subject_words.extend(words)
            
            if not subject_words:
                return {}
            
            # Find most common subject words
            word_counter = Counter(subject_words)
            common_words = [word for word, count in word_counter.most_common(20) if count >= 2]
            
            if common_words:
                return {'subject_patterns': common_words}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing subject patterns: {e}")
            return {}

    def _analyze_phrase_patterns(self, texts: List[str]) -> Dict[str, List[str]]:
        """Analyze common phrases for topics"""
        try:
            phrases = self.text_processor.extract_common_phrases(texts, min_length=2, max_length=4)
            
            if not phrases:
                return {}
            
            # Group similar phrases
            common_phrases = [phrase for phrase, count in phrases[:15] if count >= 3]
            
            if common_phrases:
                return {'common_phrases': common_phrases}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing phrase patterns: {e}")
            return {}

    def _calculate_word_importance(self, all_words: List[str], email_word_sets: List[Set[str]]) -> Dict[str, float]:
        """Calculate importance scores for words using TF-IDF-like approach"""
        try:
            word_counter = Counter(all_words)
            total_emails = len(email_word_sets)
            
            word_scores = {}
            
            for word, tf in word_counter.items():
                if tf < 2:  # Skip very rare words
                    continue
                
                # Document frequency
                df = sum(1 for word_set in email_word_sets if word in word_set)
                
                # TF-IDF score
                idf = math.log(total_emails / df) if df > 0 else 0
                score = tf * idf
                
                word_scores[word] = score
            
            return word_scores
            
        except Exception as e:
            logger.error(f"Error calculating word importance: {e}")
            return {}

    def _cluster_words_into_topics(self, word_scores: Dict[str, float]) -> Dict[str, List[str]]:
        """Cluster words into topics based on similarity and importance"""
        try:
            # Simple clustering based on business domain keywords
            clustered_topics = defaultdict(list)
            used_words = set()
            
            # Match words to business domains
            for domain, keywords in self.business_keywords.items():
                for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True):
                    if word in used_words:
                        continue
                    
                    # Check if word is related to this domain
                    if any(keyword in word or word in keyword for keyword in keywords):
                        clustered_topics[domain].append(word)
                        used_words.add(word)
                        
                        if len(clustered_topics[domain]) >= 10:  # Limit words per topic
                            break
            
            # Create a general topic for remaining high-scoring words
            general_words = []
            for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True):
                if word not in used_words and len(general_words) < 15:
                    general_words.append(word)
            
            if general_words:
                clustered_topics['general'] = general_words
            
            return dict(clustered_topics)
            
        except Exception as e:
            logger.error(f"Error clustering words into topics: {e}")
            return {}

    def _combine_topic_results(self, *topic_dicts) -> Dict[str, List[str]]:
        """Combine multiple topic extraction results"""
        try:
            combined = defaultdict(set)
            
            for topic_dict in topic_dicts:
                for topic, words in topic_dict.items():
                    combined[topic].update(words)
            
            # Convert to lists and limit size
            result = {}
            for topic, word_set in combined.items():
                if len(word_set) >= 3:  # Only keep topics with sufficient words
                    result[topic] = list(word_set)[:20]  # Limit to top 20 words
            
            return result
            
        except Exception as e:
            logger.error(f"Error combining topic results: {e}")
            return {}

    def _categorize_client_business(self, emails: List[EmailMessage]) -> str:
        """Categorize a client's business type based on their emails"""
        try:
            all_text = ""
            for email in emails:
                if email.body_text:
                    all_text += " " + email.body_text
                if email.subject:
                    all_text += " " + email.subject
            
            all_text = all_text.lower()
            
            # Score each business category
            category_scores = {}
            for category, keywords in self.business_keywords.items():
                score = sum(all_text.count(keyword) for keyword in keywords)
                if score > 0:
                    category_scores[category] = score
            
            if category_scores:
                return max(category_scores, key=category_scores.get)
            else:
                return 'general'
                
        except Exception as e:
            logger.error(f"Error categorizing client business: {e}")
            return 'general'

    def _extract_questions(self, emails: List[EmailMessage]) -> List[str]:
        """Extract questions from incoming emails"""
        try:
            questions = []
            
            for email in emails:
                if not email.body_text:
                    continue
                
                # Find sentences ending with question marks
                sentences = re.split(r'[.!?]+', email.body_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if '?' in sentence or sentence.lower().startswith(('what', 'how', 'when', 'where', 'why', 'can', 'could', 'would', 'do', 'does')):
                        if 10 <= len(sentence) <= 200:  # Reasonable length
                            questions.append(sentence)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return []

    def _extract_requests(self, emails: List[EmailMessage]) -> List[str]:
        """Extract requests from incoming emails"""
        try:
            requests = []
            
            request_patterns = [
                r'please\s+(.{10,100})',
                r'could\s+you\s+(.{10,100})',
                r'would\s+you\s+(.{10,100})',
                r'can\s+you\s+(.{10,100})',
                r'i\s+need\s+(.{10,100})',
                r'we\s+need\s+(.{10,100})',
            ]
            
            for email in emails:
                if not email.body_text:
                    continue
                
                text = email.body_text.lower()
                for pattern in request_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        match = match.strip()
                        if match and len(match) >= 10:
                            requests.append(match)
            
            return requests
            
        except Exception as e:
            logger.error(f"Error extracting requests: {e}")
            return []

    def _rank_common_queries(self, queries: List[str]) -> List[str]:
        """Rank queries by similarity and frequency"""
        try:
            if not queries:
                return []
            
            # Simple frequency-based ranking
            query_counter = Counter()
            
            for query in queries:
                # Normalize query
                normalized = re.sub(r'[^\w\s]', '', query.lower()).strip()
                if len(normalized) >= 10:
                    query_counter[normalized] += 1
            
            # Return most common queries
            return [query for query, count in query_counter.most_common() if count >= 2]
            
        except Exception as e:
            logger.error(f"Error ranking common queries: {e}")
            return []

    def _extract_email_address(self, email_string: str) -> Optional[str]:
        """Extract clean email address from email string"""
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

    def _load_business_keywords(self) -> Dict[str, List[str]]:
        """Load business domain keywords"""
        return {
            'technology': [
                'software', 'development', 'programming', 'code', 'api', 'database',
                'web', 'mobile', 'app', 'system', 'technical', 'digital', 'platform',
                'integration', 'deployment', 'testing', 'bug', 'feature', 'update'
            ],
            'finance': [
                'budget', 'cost', 'price', 'payment', 'invoice', 'billing', 'financial',
                'accounting', 'revenue', 'profit', 'investment', 'expense', 'tax',
                'contract', 'proposal', 'quote', 'estimate', 'purchase'
            ],
            'marketing': [
                'campaign', 'brand', 'advertising', 'promotion', 'marketing', 'social',
                'content', 'email', 'newsletter', 'website', 'seo', 'analytics',
                'customer', 'audience', 'engagement', 'conversion', 'traffic'
            ],
            'sales': [
                'sales', 'client', 'customer', 'prospect', 'deal', 'lead', 'pipeline',
                'demo', 'presentation', 'proposal', 'negotiation', 'closing', 'revenue',
                'target', 'quota', 'commission', 'relationship'
            ],
            'project_management': [
                'project', 'deadline', 'milestone', 'task', 'timeline', 'schedule',
                'resource', 'team', 'coordination', 'planning', 'status', 'progress',
                'deliverable', 'requirement', 'scope', 'risk', 'issue'
            ],
            'support': [
                'support', 'help', 'issue', 'problem', 'question', 'troubleshoot',
                'fix', 'solution', 'assistance', 'ticket', 'bug', 'error',
                'documentation', 'guide', 'tutorial', 'training'
            ],
            'legal': [
                'legal', 'contract', 'agreement', 'terms', 'conditions', 'compliance',
                'policy', 'regulation', 'law', 'attorney', 'counsel', 'liability',
                'intellectual', 'property', 'copyright', 'trademark'
            ],
            'hr': [
                'employee', 'hiring', 'recruitment', 'candidate', 'interview', 'onboarding',
                'training', 'performance', 'review', 'salary', 'benefits', 'policy',
                'hr', 'human', 'resources', 'team', 'staff'
            ]
        }

    def _load_topic_keywords(self) -> Dict[str, List[str]]:
        """Load topic-specific keywords"""
        return {
            'meetings': ['meeting', 'call', 'conference', 'zoom', 'teams', 'agenda', 'schedule'],
            'deadlines': ['deadline', 'due', 'urgent', 'asap', 'timeline', 'schedule'],
            'reports': ['report', 'analysis', 'data', 'metrics', 'dashboard', 'summary'],
            'proposals': ['proposal', 'quote', 'estimate', 'bid', 'offer', 'pricing'],
            'feedback': ['feedback', 'review', 'comments', 'suggestions', 'improvement'],
            'updates': ['update', 'progress', 'status', 'news', 'changes', 'announcement'],
            'collaboration': ['collaborate', 'teamwork', 'partnership', 'cooperation', 'joint'],
            'planning': ['plan', 'strategy', 'roadmap', 'goals', 'objectives', 'vision']
        }