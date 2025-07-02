import logging
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import re

from src.models.email import EmailMessage
from src.models.response import WritingStyleProfile
from src.utils.text_processing import TextProcessor
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

@dataclass
class StyleAnalysisResult:
    """Writing style analysis result"""
    avg_sentence_length: float
    avg_paragraph_length: float
    vocabulary_complexity: float
    readability_score: float
    formality_score: float
    politeness_score: float
    assertiveness_score: float
    emotional_tone: str
    common_phrases: List[str]
    signature_patterns: List[str]
    greeting_patterns: List[str]
    closing_patterns: List[str]
    avg_response_time_hours: float
    preferred_response_length: str
    use_bullet_points: bool
    use_numbered_lists: bool
    exclamation_frequency: float
    question_frequency: float
    emoji_usage: bool
    formatting_preferences: Dict[str, bool]
    emails_analyzed: int
    confidence_score: float

class WritingStyleAnalyzer:
    """
    Advanced natural language processing for writing style analysis
    Extracts linguistic patterns, formality levels, and communication preferences
    """
    
    def __init__(self):
        self.text_processor = TextProcessor()
        
    async def analyze_writing_style(self, user_id: str) -> Optional[StyleAnalysisResult]:
        """
        Comprehensive analysis of user's writing patterns
        
        Args:
            user_id: User identifier
            
        Returns:
            Writing style analysis result
        """
        try:
            logger.info(f"Starting writing style analysis for user {user_id}")
            
            async with AsyncSessionLocal() as session:
                # Get user's outgoing emails (their writing)
                outgoing_emails = await self._get_outgoing_emails(user_id, session)
                
                if len(outgoing_emails) < 5:
                    logger.warning(f"Insufficient emails for analysis: {len(outgoing_emails)}")
                    return None
                
                # Perform comprehensive analysis
                result = await self._perform_style_analysis(outgoing_emails)
                
                # Save or update style profile in database
                await self._save_style_profile(user_id, result, session)
                await session.commit()
                
                logger.info(f"Completed writing style analysis for user {user_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error in analyze_writing_style: {e}")
            return None

    async def _get_outgoing_emails(self, user_id: str, session) -> List[EmailMessage]:
        """
        Get user's outgoing emails for style analysis
        
        Args:
            user_id: User identifier
            session: Database session
            
        Returns:
            List of outgoing email messages
        """
        try:
            from sqlalchemy import select
            
            stmt = select(EmailMessage).where(
                EmailMessage.user_id == user_id,
                EmailMessage.direction == 'outgoing',
                EmailMessage.body_text.isnot(None),
                EmailMessage.body_text != ''
            ).order_by(EmailMessage.sent_datetime.desc()).limit(500)  # Analyze up to 500 recent emails
            
            result = await session.execute(stmt)
            emails = result.scalars().all()
            
            return list(emails)
            
        except Exception as e:
            logger.error(f"Error fetching outgoing emails: {e}")
            return []

    async def _perform_style_analysis(self, emails: List[EmailMessage]) -> StyleAnalysisResult:
        """
        Perform comprehensive style analysis on emails
        
        Args:
            emails: List of email messages to analyze
            
        Returns:
            Style analysis result
        """
        try:
            # Extract text content
            email_texts = []
            email_subjects = []
            
            for email in emails:
                if email.body_text:
                    email_texts.append(email.body_text)
                if email.subject:
                    email_subjects.append(email.subject)
            
            # Basic linguistic analysis
            linguistic_stats = self._analyze_linguistic_patterns(email_texts)
            
            # Communication patterns
            communication_patterns = self._analyze_communication_patterns(emails)
            
            # Formatting preferences
            formatting_prefs = self._analyze_formatting_preferences(email_texts)
            
            # Extract patterns
            common_phrases = self._extract_common_phrases(email_texts)
            signature_patterns = self._extract_signature_patterns(email_texts)
            greeting_patterns = self._extract_greeting_patterns(email_texts)
            closing_patterns = self._extract_closing_patterns(email_texts)
            
            # Response time analysis
            avg_response_time = self._calculate_average_response_time(emails)
            
            # Emotional tone analysis
            emotional_tone = self._analyze_emotional_tone(email_texts)
            
            # Assertiveness analysis
            assertiveness_score = self._analyze_assertiveness(email_texts)
            
            # Calculate confidence score based on sample size and consistency
            confidence_score = self._calculate_confidence_score(len(emails), linguistic_stats)
            
            return StyleAnalysisResult(
                avg_sentence_length=linguistic_stats['avg_sentence_length'],
                avg_paragraph_length=linguistic_stats['avg_paragraph_length'],
                vocabulary_complexity=linguistic_stats['vocabulary_complexity'],
                readability_score=linguistic_stats['readability_score'],
                formality_score=linguistic_stats['formality_score'],
                politeness_score=linguistic_stats['politeness_score'],
                assertiveness_score=assertiveness_score,
                emotional_tone=emotional_tone,
                common_phrases=common_phrases,
                signature_patterns=signature_patterns,
                greeting_patterns=greeting_patterns,
                closing_patterns=closing_patterns,
                avg_response_time_hours=avg_response_time,
                preferred_response_length=communication_patterns['preferred_length'],
                use_bullet_points=formatting_prefs['use_bullet_points'],
                use_numbered_lists=formatting_prefs['use_numbered_lists'],
                exclamation_frequency=formatting_prefs['exclamation_frequency'],
                question_frequency=formatting_prefs['question_frequency'],
                emoji_usage=formatting_prefs['emoji_usage'],
                formatting_preferences=formatting_prefs,
                emails_analyzed=len(emails),
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error performing style analysis: {e}")
            raise

    def _analyze_linguistic_patterns(self, texts: List[str]) -> Dict[str, float]:
        """
        Analyze linguistic patterns across all texts
        
        Args:
            texts: List of email body texts
            
        Returns:
            Dictionary of linguistic statistics
        """
        try:
            all_stats = []
            
            for text in texts:
                if not text:
                    continue
                
                stats = self.text_processor.calculate_text_statistics(text)
                if stats:
                    all_stats.append(stats)
            
            if not all_stats:
                return {}
            
            # Calculate averages across all emails
            avg_stats = {}
            for key in all_stats[0].keys():
                values = [stats[key] for stats in all_stats if key in stats]
                if values:
                    avg_stats[key] = statistics.mean(values)
            
            # Add paragraph-specific analysis
            avg_stats['avg_paragraph_length'] = self._calculate_avg_paragraph_length(texts)
            avg_stats['vocabulary_complexity'] = self._calculate_vocabulary_complexity(texts)
            
            return avg_stats
            
        except Exception as e:
            logger.warning(f"Error analyzing linguistic patterns: {e}")
            return {}

    def _calculate_avg_paragraph_length(self, texts: List[str]) -> float:
        """Calculate average paragraph length across texts"""
        try:
            paragraph_lengths = []
            
            for text in texts:
                if not text:
                    continue
                
                # Split by double newlines to get paragraphs
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                
                for paragraph in paragraphs:
                    words = paragraph.split()
                    if len(words) > 5:  # Only count substantial paragraphs
                        paragraph_lengths.append(len(words))
            
            return statistics.mean(paragraph_lengths) if paragraph_lengths else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating paragraph length: {e}")
            return 0.0

    def _calculate_vocabulary_complexity(self, texts: List[str]) -> float:
        """Calculate vocabulary complexity (type-token ratio)"""
        try:
            all_words = []
            
            for text in texts:
                words = self.text_processor.extract_words(text, remove_stop_words=True)
                all_words.extend(words)
            
            if not all_words:
                return 0.0
            
            unique_words = set(all_words)
            type_token_ratio = len(unique_words) / len(all_words)
            
            # Normalize to 0-1 scale (typical values are 0.3-0.8)
            return min(1.0, type_token_ratio * 2.5)
            
        except Exception as e:
            logger.warning(f"Error calculating vocabulary complexity: {e}")
            return 0.0

    def _analyze_communication_patterns(self, emails: List[EmailMessage]) -> Dict[str, str]:
        """Analyze communication patterns"""
        try:
            email_lengths = []
            
            for email in emails:
                if email.body_text:
                    word_count = len(email.body_text.split())
                    email_lengths.append(word_count)
            
            if not email_lengths:
                return {'preferred_length': 'medium'}
            
            avg_length = statistics.mean(email_lengths)
            
            if avg_length < 50:
                preferred_length = 'short'
            elif avg_length > 200:
                preferred_length = 'long'
            else:
                preferred_length = 'medium'
            
            return {'preferred_length': preferred_length}
            
        except Exception as e:
            logger.warning(f"Error analyzing communication patterns: {e}")
            return {'preferred_length': 'medium'}

    def _analyze_formatting_preferences(self, texts: List[str]) -> Dict[str, float]:
        """Analyze formatting preferences"""
        try:
            total_texts = len(texts)
            if total_texts == 0:
                return {}
            
            bullet_count = 0
            numbered_count = 0
            exclamation_count = 0
            question_count = 0
            emoji_count = 0
            total_chars = 0
            
            for text in texts:
                if not text:
                    continue
                
                total_chars += len(text)
                
                # Check for bullet points
                if re.search(r'^\s*[\u2022\u2023\u25E6\u2043\u2219*-]\s', text, re.MULTILINE):
                    bullet_count += 1
                
                # Check for numbered lists
                if re.search(r'^\s*\d+\.\s', text, re.MULTILINE):
                    numbered_count += 1
                
                # Count punctuation
                exclamation_count += text.count('!')
                question_count += text.count('?')
                
                # Check for emojis (basic detection)
                emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]')
                if emoji_pattern.search(text):
                    emoji_count += 1
            
            return {
                'use_bullet_points': bullet_count / total_texts > 0.1,
                'use_numbered_lists': numbered_count / total_texts > 0.05,
                'exclamation_frequency': exclamation_count / max(1, total_chars) * 1000,  # Per 1000 chars
                'question_frequency': question_count / max(1, total_chars) * 1000,
                'emoji_usage': emoji_count / total_texts > 0.05
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing formatting preferences: {e}")
            return {}

    def _extract_common_phrases(self, texts: List[str]) -> List[str]:
        """Extract common phrases used by the user"""
        try:
            phrases = self.text_processor.extract_common_phrases(texts, min_length=2, max_length=6)
            return [phrase for phrase, count in phrases[:10] if count >= 2]
            
        except Exception as e:
            logger.warning(f"Error extracting common phrases: {e}")
            return []

    def _extract_signature_patterns(self, texts: List[str]) -> List[str]:
        """Extract common signature patterns"""
        try:
            signature_patterns = []
            
            for text in texts:
                if not text:
                    continue
                
                # Look for signature-like patterns at the end
                lines = text.strip().split('\n')
                if len(lines) >= 2:
                    last_lines = lines[-3:]  # Last 3 lines
                    
                    for line in last_lines:
                        line = line.strip()
                        if line and len(line) < 100:  # Reasonable signature length
                            # Check if it looks like a signature
                            if any(pattern in line.lower() for pattern in 
                                   ['best', 'regards', 'sincerely', 'thanks', 'cheers']):
                                signature_patterns.append(line)
            
            # Return most common signatures
            counter = Counter(signature_patterns)
            return [sig for sig, count in counter.most_common(5) if count >= 2]
            
        except Exception as e:
            logger.warning(f"Error extracting signature patterns: {e}")
            return []

    def _extract_greeting_patterns(self, texts: List[str]) -> List[str]:
        """Extract common greeting patterns"""
        try:
            greeting_patterns = []
            
            for text in texts:
                if not text:
                    continue
                
                # Look for greetings at the beginning
                lines = text.strip().split('\n')
                if lines:
                    first_line = lines[0].strip()
                    if first_line and len(first_line) < 100:
                        # Check if it looks like a greeting
                        if any(pattern in first_line.lower() for pattern in 
                               ['hi', 'hello', 'dear', 'good morning', 'good afternoon']):
                            greeting_patterns.append(first_line)
            
            # Return most common greetings
            counter = Counter(greeting_patterns)
            return [greeting for greeting, count in counter.most_common(5) if count >= 2]
            
        except Exception as e:
            logger.warning(f"Error extracting greeting patterns: {e}")
            return []

    def _extract_closing_patterns(self, texts: List[str]) -> List[str]:
        """Extract common closing patterns"""
        try:
            closing_patterns = []
            
            for text in texts:
                if not text:
                    continue
                
                # Look for closings before signature
                lines = text.strip().split('\n')
                if len(lines) >= 2:
                    # Check second-to-last or third-to-last line
                    for line in lines[-3:-1]:
                        line = line.strip()
                        if line and len(line) < 50:
                            if any(pattern in line.lower() for pattern in 
                                   ['thank', 'best', 'look forward', 'let me know']):
                                closing_patterns.append(line)
            
            # Return most common closings
            counter = Counter(closing_patterns)
            return [closing for closing, count in counter.most_common(5) if count >= 2]
            
        except Exception as e:
            logger.warning(f"Error extracting closing patterns: {e}")
            return []

    def _calculate_average_response_time(self, emails: List[EmailMessage]) -> float:
        """Calculate average response time based on email timestamps"""
        # This is simplified - in a real implementation, you'd need to match
        # emails to their responses based on thread IDs
        try:
            # For now, return a default value
            return 4.0  # 4 hours default
            
        except Exception as e:
            logger.warning(f"Error calculating response time: {e}")
            return 24.0

    def _analyze_emotional_tone(self, texts: List[str]) -> str:
        """Analyze overall emotional tone"""
        try:
            positive_words = ['great', 'excellent', 'wonderful', 'amazing', 'fantastic', 'perfect', 'love', 'excited']
            negative_words = ['terrible', 'awful', 'horrible', 'hate', 'annoying', 'frustrated', 'disappointed']
            neutral_words = ['okay', 'fine', 'acceptable', 'reasonable', 'standard']
            
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for text in texts:
                if not text:
                    continue
                
                text_lower = text.lower()
                positive_count += sum(1 for word in positive_words if word in text_lower)
                negative_count += sum(1 for word in negative_words if word in text_lower)
                neutral_count += sum(1 for word in neutral_words if word in text_lower)
            
            total_emotional_words = positive_count + negative_count + neutral_count
            
            if total_emotional_words == 0:
                return 'neutral'
            
            positive_ratio = positive_count / total_emotional_words
            negative_ratio = negative_count / total_emotional_words
            
            if positive_ratio > negative_ratio * 2:
                return 'positive'
            elif negative_ratio > positive_ratio * 2:
                return 'negative'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.warning(f"Error analyzing emotional tone: {e}")
            return 'neutral'

    def _analyze_assertiveness(self, texts: List[str]) -> float:
        """Analyze assertiveness level"""
        try:
            assertive_indicators = ['must', 'need', 'require', 'expect', 'demand', 'should', 'will']
            tentative_indicators = ['maybe', 'perhaps', 'might', 'could', 'possibly', 'if possible']
            
            assertive_count = 0
            tentative_count = 0
            
            for text in texts:
                if not text:
                    continue
                
                text_lower = text.lower()
                assertive_count += sum(1 for indicator in assertive_indicators if indicator in text_lower)
                tentative_count += sum(1 for indicator in tentative_indicators if indicator in text_lower)
            
            total_indicators = assertive_count + tentative_count
            
            if total_indicators == 0:
                return 0.5  # Neutral
            
            assertiveness_ratio = assertive_count / total_indicators
            return assertiveness_ratio
            
        except Exception as e:
            logger.warning(f"Error analyzing assertiveness: {e}")
            return 0.5

    def _calculate_confidence_score(self, email_count: int, linguistic_stats: Dict) -> float:
        """Calculate confidence score for the analysis"""
        try:
            # Base confidence on sample size
            if email_count >= 50:
                sample_confidence = 1.0
            elif email_count >= 20:
                sample_confidence = 0.8
            elif email_count >= 10:
                sample_confidence = 0.6
            else:
                sample_confidence = 0.4
            
            # Adjust based on data quality
            data_quality = 1.0
            if not linguistic_stats:
                data_quality = 0.5
            
            return sample_confidence * data_quality
            
        except Exception as e:
            logger.warning(f"Error calculating confidence score: {e}")
            return 0.5

    async def _save_style_profile(self, user_id: str, analysis: StyleAnalysisResult, session):
        """Save or update writing style profile in database"""
        try:
            from sqlalchemy import select
            
            # Check if profile already exists
            stmt = select(WritingStyleProfile).where(WritingStyleProfile.user_id == user_id)
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            
            if profile:
                # Update existing profile
                profile.avg_sentence_length = analysis.avg_sentence_length
                profile.avg_paragraph_length = analysis.avg_paragraph_length
                profile.vocabulary_complexity = analysis.vocabulary_complexity
                profile.readability_score = analysis.readability_score
                profile.formality_score = analysis.formality_score
                profile.politeness_score = analysis.politeness_score
                profile.assertiveness_score = analysis.assertiveness_score
                profile.emotional_tone = analysis.emotional_tone
                profile.common_phrases = analysis.common_phrases
                profile.signature_patterns = analysis.signature_patterns
                profile.greeting_patterns = analysis.greeting_patterns
                profile.closing_patterns = analysis.closing_patterns
                profile.avg_response_time_hours = analysis.avg_response_time_hours
                profile.preferred_response_length = analysis.preferred_response_length
                profile.use_bullet_points = analysis.use_bullet_points
                profile.use_numbered_lists = analysis.use_numbered_lists
                profile.exclamation_frequency = analysis.exclamation_frequency
                profile.question_frequency = analysis.question_frequency
                profile.emoji_usage = analysis.emoji_usage
                profile.formatting_preferences = analysis.formatting_preferences
                profile.emails_analyzed = analysis.emails_analyzed
                profile.confidence_score = analysis.confidence_score
                profile.last_analysis = datetime.utcnow()
                profile.updated_at = datetime.utcnow()
                
                logger.info(f"Updated writing style profile for user {user_id}")
            else:
                # Create new profile
                profile = WritingStyleProfile(
                    user_id=user_id,
                    avg_sentence_length=analysis.avg_sentence_length,
                    avg_paragraph_length=analysis.avg_paragraph_length,
                    vocabulary_complexity=analysis.vocabulary_complexity,
                    readability_score=analysis.readability_score,
                    formality_score=analysis.formality_score,
                    politeness_score=analysis.politeness_score,
                    assertiveness_score=analysis.assertiveness_score,
                    emotional_tone=analysis.emotional_tone,
                    common_phrases=analysis.common_phrases,
                    signature_patterns=analysis.signature_patterns,
                    greeting_patterns=analysis.greeting_patterns,
                    closing_patterns=analysis.closing_patterns,
                    avg_response_time_hours=analysis.avg_response_time_hours,
                    preferred_response_length=analysis.preferred_response_length,
                    use_bullet_points=analysis.use_bullet_points,
                    use_numbered_lists=analysis.use_numbered_lists,
                    exclamation_frequency=analysis.exclamation_frequency,
                    question_frequency=analysis.question_frequency,
                    emoji_usage=analysis.emoji_usage,
                    formatting_preferences=analysis.formatting_preferences,
                    emails_analyzed=analysis.emails_analyzed,
                    confidence_score=analysis.confidence_score,
                    last_analysis=datetime.utcnow()
                )
                
                session.add(profile)
                logger.info(f"Created new writing style profile for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error saving style profile: {e}")
            raise