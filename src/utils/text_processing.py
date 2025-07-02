import re
import string
from typing import List, Dict, Set, Optional, Tuple
import logging
from collections import Counter
import statistics

logger = logging.getLogger(__name__)

class TextProcessor:
    """
    Advanced text processing utilities for email analysis
    Provides linguistic analysis and text normalization functions
    """
    
    def __init__(self):
        self.stop_words = self._load_stop_words()
        self.formality_markers = self._load_formality_markers()
        self.politeness_markers = self._load_politeness_markers()
        
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text for analysis
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        try:
            # Remove HTML tags if any remain
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove email signatures (common patterns)
            text = self._remove_email_signature(text)
            
            # Remove quoted text (replies)
            text = self._remove_quoted_text(text)
            
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            # Remove excessive punctuation
            text = re.sub(r'[!]{2,}', '!', text)
            text = re.sub(r'[?]{2,}', '?', text)
            text = re.sub(r'[.]{3,}', '...', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning text: {e}")
            return text

    def _remove_email_signature(self, text: str) -> str:
        """Remove email signature from text"""
        try:
            # Common signature patterns
            signature_patterns = [
                r'--\s*\n.*$',  # -- separator
                r'Best regards,.*$',
                r'Sincerely,.*$',
                r'Thanks,.*$',
                r'Regards,.*$',
                r'Sent from my.*$',
                r'Get Outlook for.*$',
            ]
            
            for pattern in signature_patterns:
                text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error removing signature: {e}")
            return text

    def _remove_quoted_text(self, text: str) -> str:
        """Remove quoted text from email replies"""
        try:
            # Common quote patterns
            quote_patterns = [
                r'^>.*$',  # Lines starting with >
                r'On .* wrote:.*$',  # Gmail quote style
                r'From:.*$',  # Outlook quote style
                r'-----Original Message-----.*$',  # Outlook original message
            ]
            
            lines = text.split('\n')
            filtered_lines = []
            
            in_quote = False
            for line in lines:
                # Check if line starts a quote block
                if any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in quote_patterns):
                    in_quote = True
                    continue
                
                # Check if line is quoted
                if line.strip().startswith('>'):
                    continue
                
                # If we're in a quote and hit a non-quoted line, we might be out
                if in_quote and line.strip() and not line.strip().startswith('>'):
                    # Check if it looks like continuation of quote or new content
                    if len(line.strip()) > 50:  # Likely new content
                        in_quote = False
                
                if not in_quote:
                    filtered_lines.append(line)
            
            return '\n'.join(filtered_lines)
            
        except Exception as e:
            logger.warning(f"Error removing quoted text: {e}")
            return text

    def extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        try:
            if not text:
                return []
            
            # Split on sentence endings, but be careful with abbreviations
            sentences = re.split(r'[.!?]+\s+', text)
            
            # Filter out very short sentences (likely not real sentences)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            return sentences
            
        except Exception as e:
            logger.warning(f"Error extracting sentences: {e}")
            return []

    def extract_words(self, text: str, remove_stop_words: bool = True) -> List[str]:
        """
        Extract words from text
        
        Args:
            text: Input text
            remove_stop_words: Whether to remove common stop words
            
        Returns:
            List of words
        """
        try:
            if not text:
                return []
            
            # Convert to lowercase and remove punctuation
            text = text.lower()
            text = text.translate(str.maketrans('', '', string.punctuation))
            
            # Split into words
            words = text.split()
            
            # Remove stop words if requested
            if remove_stop_words:
                words = [word for word in words if word not in self.stop_words]
            
            # Filter out very short words
            words = [word for word in words if len(word) > 2]
            
            return words
            
        except Exception as e:
            logger.warning(f"Error extracting words: {e}")
            return []

    def calculate_readability_score(self, text: str) -> float:
        """
        Calculate readability score (simplified Flesch Reading Ease)
        
        Args:
            text: Input text
            
        Returns:
            Readability score (0-100, higher = more readable)
        """
        try:
            if not text:
                return 0.0
            
            sentences = self.extract_sentences(text)
            if not sentences:
                return 0.0
            
            words = self.extract_words(text, remove_stop_words=False)
            if not words:
                return 0.0
            
            # Count syllables (simplified)
            total_syllables = sum(self._count_syllables(word) for word in words)
            
            # Flesch Reading Ease formula
            avg_sentence_length = len(words) / len(sentences)
            avg_syllables_per_word = total_syllables / len(words)
            
            score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            
            # Clamp to 0-100 range
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.warning(f"Error calculating readability: {e}")
            return 50.0  # Default middle score

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified approach)"""
        try:
            word = word.lower()
            count = 0
            vowels = 'aeiouy'
            
            if word[0] in vowels:
                count += 1
            
            for index in range(1, len(word)):
                if word[index] in vowels and word[index - 1] not in vowels:
                    count += 1
            
            if word.endswith('e'):
                count -= 1
            
            if count == 0:
                count = 1
            
            return count
            
        except Exception:
            return 1

    def analyze_formality(self, text: str) -> float:
        """
        Analyze formality level of text
        
        Args:
            text: Input text
            
        Returns:
            Formality score (0-1, higher = more formal)
        """
        try:
            if not text:
                return 0.5
            
            text_lower = text.lower()
            
            formal_score = 0
            informal_score = 0
            
            # Count formal markers
            for marker in self.formality_markers['formal']:
                formal_score += text_lower.count(marker)
            
            # Count informal markers
            for marker in self.formality_markers['informal']:
                informal_score += text_lower.count(marker)
            
            # Additional heuristics
            # Contractions indicate informality
            contractions = ["don't", "won't", "can't", "I'm", "you're", "it's", "we're"]
            informal_score += sum(text_lower.count(contraction) for contraction in contractions)
            
            # Exclamation marks indicate informality
            informal_score += text.count('!')
            
            # Calculate formality ratio
            total_markers = formal_score + informal_score
            if total_markers == 0:
                return 0.5  # Neutral
            
            formality_ratio = formal_score / total_markers
            return formality_ratio
            
        except Exception as e:
            logger.warning(f"Error analyzing formality: {e}")
            return 0.5

    def analyze_politeness(self, text: str) -> float:
        """
        Analyze politeness level of text
        
        Args:
            text: Input text
            
        Returns:
            Politeness score (0-1, higher = more polite)
        """
        try:
            if not text:
                return 0.5
            
            text_lower = text.lower()
            
            politeness_score = 0
            total_indicators = 0
            
            # Count politeness markers
            for category, markers in self.politeness_markers.items():
                for marker in markers:
                    count = text_lower.count(marker)
                    politeness_score += count
                    total_indicators += count
            
            # Question marks can indicate politeness (asking rather than demanding)
            question_marks = text.count('?')
            politeness_score += question_marks * 0.5
            total_indicators += question_marks
            
            if total_indicators == 0:
                return 0.5  # Neutral
            
            # Normalize to 0-1 scale
            return min(1.0, politeness_score / max(1, total_indicators))
            
        except Exception as e:
            logger.warning(f"Error analyzing politeness: {e}")
            return 0.5

    def extract_common_phrases(self, texts: List[str], min_length: int = 3, max_length: int = 10) -> List[Tuple[str, int]]:
        """
        Extract common phrases from multiple texts
        
        Args:
            texts: List of text documents
            min_length: Minimum phrase length in words
            max_length: Maximum phrase length in words
            
        Returns:
            List of (phrase, frequency) tuples
        """
        try:
            phrase_counter = Counter()
            
            for text in texts:
                if not text:
                    continue
                
                # Clean and tokenize
                clean_text = self.clean_text(text)
                words = clean_text.lower().split()
                
                # Extract n-grams
                for n in range(min_length, max_length + 1):
                    for i in range(len(words) - n + 1):
                        phrase = ' '.join(words[i:i + n])
                        
                        # Filter out phrases with too many stop words
                        phrase_words = phrase.split()
                        stop_word_ratio = sum(1 for w in phrase_words if w in self.stop_words) / len(phrase_words)
                        
                        if stop_word_ratio < 0.8:  # Less than 80% stop words
                            phrase_counter[phrase] += 1
            
            # Return most common phrases
            return phrase_counter.most_common(20)
            
        except Exception as e:
            logger.warning(f"Error extracting common phrases: {e}")
            return []

    def calculate_text_statistics(self, text: str) -> Dict[str, float]:
        """
        Calculate comprehensive text statistics
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of text statistics
        """
        try:
            if not text:
                return {}
            
            sentences = self.extract_sentences(text)
            words = self.extract_words(text, remove_stop_words=False)
            
            if not sentences or not words:
                return {}
            
            # Basic counts
            char_count = len(text)
            word_count = len(words)
            sentence_count = len(sentences)
            
            # Calculate averages
            avg_sentence_length = word_count / sentence_count
            avg_word_length = sum(len(word) for word in words) / word_count
            
            # Sentence length distribution
            sentence_lengths = [len(sentence.split()) for sentence in sentences]
            sentence_length_std = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
            
            # Vocabulary diversity (unique words / total words)
            unique_words = set(words)
            vocabulary_diversity = len(unique_words) / word_count
            
            return {
                'character_count': char_count,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'avg_sentence_length': avg_sentence_length,
                'avg_word_length': avg_word_length,
                'sentence_length_std': sentence_length_std,
                'vocabulary_diversity': vocabulary_diversity,
                'readability_score': self.calculate_readability_score(text),
                'formality_score': self.analyze_formality(text),
                'politeness_score': self.analyze_politeness(text)
            }
            
        except Exception as e:
            logger.warning(f"Error calculating text statistics: {e}")
            return {}

    def _load_stop_words(self) -> Set[str]:
        """Load common English stop words"""
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'would', 'i', 'you', 'we', 'they',
            'this', 'these', 'those', 'have', 'had', 'been', 'their', 'there',
            'where', 'when', 'what', 'who', 'how', 'why', 'can', 'could',
            'should', 'would', 'may', 'might', 'must', 'shall', 'do', 'does',
            'did', 'get', 'got', 'go', 'goes', 'went', 'come', 'came', 'take',
            'took', 'see', 'saw', 'know', 'knew', 'think', 'thought', 'say',
            'said', 'tell', 'told', 'ask', 'asked', 'give', 'gave', 'make',
            'made', 'work', 'worked', 'call', 'called', 'try', 'tried', 'need',
            'needed', 'feel', 'felt', 'become', 'became', 'leave', 'left',
            'put', 'mean', 'meant', 'keep', 'kept', 'let', 'begin', 'began',
            'seem', 'seemed', 'help', 'helped', 'talk', 'talked', 'turn',
            'turned', 'start', 'started', 'show', 'showed', 'hear', 'heard',
            'play', 'played', 'run', 'ran', 'move', 'moved', 'live', 'lived',
            'believe', 'believed', 'hold', 'held', 'bring', 'brought', 'happen',
            'happened', 'write', 'wrote', 'provide', 'provided', 'sit', 'sat',
            'stand', 'stood', 'lose', 'lost', 'pay', 'paid', 'meet', 'met',
            'include', 'included', 'continue', 'continued', 'set', 'learn',
            'learned', 'change', 'changed', 'lead', 'led', 'understand',
            'understood', 'watch', 'watched', 'follow', 'followed', 'stop',
            'stopped', 'create', 'created', 'speak', 'spoke', 'read', 'allow',
            'allowed', 'add', 'added', 'spend', 'spent', 'grow', 'grew', 'open',
            'opened', 'walk', 'walked', 'win', 'won', 'offer', 'offered',
            'remember', 'remembered', 'love', 'loved', 'consider', 'considered',
            'appear', 'appeared', 'buy', 'bought', 'wait', 'waited', 'serve',
            'served', 'die', 'died', 'send', 'sent', 'expect', 'expected',
            'build', 'built', 'stay', 'stayed', 'fall', 'fell', 'cut', 'reach',
            'reached', 'kill', 'killed', 'remain', 'remained'
        }

    def _load_formality_markers(self) -> Dict[str, List[str]]:
        """Load formality markers"""
        return {
            'formal': [
                'dear sir', 'dear madam', 'to whom it may concern',
                'yours sincerely', 'yours faithfully', 'best regards',
                'kind regards', 'respectfully', 'furthermore', 'moreover',
                'therefore', 'consequently', 'in conclusion', 'in summary',
                'please find attached', 'i would like to', 'i am writing to',
                'i would appreciate', 'thank you for your consideration'
            ],
            'informal': [
                'hey', 'hi there', 'what\'s up', 'thanks!', 'cheers',
                'talk soon', 'catch you later', 'see ya', 'awesome',
                'cool', 'great!', 'super', 'amazing', 'fantastic'
            ]
        }

    def _load_politeness_markers(self) -> Dict[str, List[str]]:
        """Load politeness markers"""
        return {
            'please': ['please', 'kindly', 'if you could', 'would you mind'],
            'thank_you': ['thank you', 'thanks', 'grateful', 'appreciate'],
            'apology': ['sorry', 'apologize', 'excuse me', 'pardon'],
            'request': ['could you', 'would you', 'may i', 'might i'],
            'greetings': ['dear', 'hello', 'good morning', 'good afternoon'],
            'closings': ['best regards', 'sincerely', 'kind regards', 'yours truly']
        }