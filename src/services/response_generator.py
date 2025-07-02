from typing import List, Dict, Optional, Any, Tuple
import logging
from datetime import datetime
import re
import json
from dataclasses import dataclass

from src.services.rag_engine import RAGEngine
from src.services.rule_generator import RuleGeneratorService
from src.services.style_analyzer import WritingStyleAnalyzer
from src.services.ultimate_prompt_service import ultimate_prompt_service
from src.models.email import EmailMessage
from src.models.response import WritingStyleProfile, ResponseRule, GeneratedResponse
from src.models.client import Client
from src.config.database import AsyncSessionLocal
from src.config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class ResponseGenerationResult:
    """Result of response generation"""
    response_text: str
    response_type: str  # rag, template, hybrid
    confidence_score: float
    relevance_score: float
    style_match_score: float
    generation_time_ms: int
    model_used: str
    tokens_used: int
    context_sources: List[Dict]
    rule_applied: Optional[str] = None
    quality_metrics: Optional[Dict] = None

class ResponseGeneratorService:
    """
    Intelligent email response generation service
    Combines RAG, style matching, and context awareness
    """
    
    def __init__(self, 
                 rag_engine: RAGEngine,
                 rule_generator: RuleGeneratorService,
                 style_analyzer: WritingStyleAnalyzer):
        self.rag_engine = rag_engine
        self.rule_generator = rule_generator
        self.style_analyzer = style_analyzer
        
    async def generate_response(self, 
                              incoming_email: EmailMessage,
                              user_id: str,
                              generation_options: Optional[Dict] = None) -> ResponseGenerationResult:
        """
        Generate contextually appropriate email response
        
        Args:
            incoming_email: Email to respond to
            user_id: User identifier
            generation_options: Additional generation options
            
        Returns:
            Response generation result
        """
        try:
            start_time = datetime.utcnow()
            logger.info(f"Generating response for email {incoming_email.id}")
            
            # Get user context
            async with AsyncSessionLocal() as session:
                user_profile = await self._get_user_profile(user_id, session)
                client_info = await self._get_client_info(incoming_email, user_id, session)
                applicable_rules = await self._get_applicable_rules(incoming_email, user_id, session)
            
            # Generate ultimate prompt for this context
            ultimate_prompt_data = await self._generate_context_ultimate_prompt(
                incoming_email, user_id, client_info
            )
            
            # Determine generation strategy
            strategy = self._determine_generation_strategy(
                incoming_email, user_profile, client_info, applicable_rules, generation_options
            )
            
            # Generate response based on strategy using ultimate prompt
            if strategy == "rule_based":
                result = await self._generate_rule_based_response(
                    incoming_email, user_profile, applicable_rules[0], start_time, ultimate_prompt_data
                )
            elif strategy == "rag_only":
                result = await self._generate_rag_response(
                    incoming_email, user_id, user_profile, start_time, ultimate_prompt_data
                )
            elif strategy == "hybrid":
                result = await self._generate_hybrid_response(
                    incoming_email, user_id, user_profile, applicable_rules, start_time, ultimate_prompt_data
                )
            else:  # template_fallback
                result = await self._generate_template_response(
                    incoming_email, user_profile, client_info, start_time, ultimate_prompt_data
                )
            
            # Apply style matching
            result = await self._apply_style_matching(result, user_profile)
            
            # Validate response quality
            result = await self._validate_response_quality(result, incoming_email)
            
            # Store generated response
            await self._store_generated_response(result, incoming_email, user_id)
            
            logger.info(f"Response generated successfully with confidence {result.confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Return fallback response
            return await self._generate_fallback_response(incoming_email, str(e))

    async def _get_user_profile(self, user_id: str, session) -> Optional[WritingStyleProfile]:
        """Get user's writing style profile"""
        try:
            from sqlalchemy import select
            
            stmt = select(WritingStyleProfile).where(WritingStyleProfile.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def _generate_context_ultimate_prompt(
        self, 
        incoming_email: EmailMessage, 
        user_id: str, 
        client_info: Optional[Client]
    ) -> Dict[str, Any]:
        """Generate ultimate prompt for the current email context"""
        try:
            # Prepare email context for prompt generation
            email_context = {
                "subject": incoming_email.subject,
                "sender": incoming_email.sender,
                "body_length": len(incoming_email.body) if incoming_email.body else 0,
                "thread_id": incoming_email.thread_id,
                "urgency": self._detect_email_urgency(incoming_email),
                "timestamp": incoming_email.timestamp.isoformat() if incoming_email.timestamp else None
            }
            
            # Determine correspondence group based on client info
            correspondence_group = None
            if client_info:
                correspondence_group = getattr(client_info, 'business_category', None)
            
            # Generate the ultimate prompt
            prompt_data = await ultimate_prompt_service.generate_ultimate_prompt(
                user_id=user_id,
                email_context=email_context,
                correspondence_group=correspondence_group
            )
            
            logger.info(f"Generated ultimate prompt with confidence {prompt_data['confidence_score']:.2f}")
            return prompt_data
            
        except Exception as e:
            logger.error(f"Error generating ultimate prompt: {e}")
            # Return a basic fallback prompt
            return {
                "ultimate_prompt": "Jsi AI asistent pro e-mailovou komunikaci. Odpověz přiměřeně a profesionálně.",
                "confidence_score": 0.5,
                "personalization_level": "basic"
            }
    
    def _detect_email_urgency(self, email: EmailMessage) -> str:
        """Detect email urgency based on content and metadata"""
        try:
            urgent_indicators = [
                "urgent", "asap", "immediately", "emergency", "critical",
                "naléhavé", "okamžitě", "nutné", "kritické", "urgentní"
            ]
            
            content = f"{email.subject} {email.body}".lower()
            
            for indicator in urgent_indicators:
                if indicator in content:
                    return "high"
            
            # Check for time-sensitive words
            time_sensitive = [
                "today", "tonight", "deadline", "expires", "closing",
                "dnes", "zítra", "termín", "uzávěrka", "končí"
            ]
            
            for indicator in time_sensitive:
                if indicator in content:
                    return "medium"
            
            return "normal"
            
        except Exception as e:
            logger.error(f"Error detecting email urgency: {e}")
            return "normal"

    async def _get_client_info(self, email: EmailMessage, user_id: str, session) -> Optional[Client]:
        """Get client information for the email sender"""
        try:
            from sqlalchemy import select
            
            # Extract sender email
            sender_email = self._extract_email_address(email.sender)
            if not sender_email:
                return None
            
            stmt = select(Client).where(
                Client.user_id == user_id,
                Client.email_address == sender_email
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting client info: {e}")
            return None

    async def _get_applicable_rules(self, email: EmailMessage, user_id: str, session) -> List[ResponseRule]:
        """Get applicable response rules for the email"""
        try:
            from sqlalchemy import select
            
            stmt = select(ResponseRule).where(
                ResponseRule.user_id == user_id,
                ResponseRule.is_active == True
            ).order_by(ResponseRule.priority.asc())
            
            result = await session.execute(stmt)
            all_rules = result.scalars().all()
            
            # Filter rules that match the email
            applicable_rules = []
            for rule in all_rules:
                if await self._rule_matches_email(rule, email):
                    applicable_rules.append(rule)
            
            return applicable_rules
            
        except Exception as e:
            logger.error(f"Error getting applicable rules: {e}")
            return []

    async def _rule_matches_email(self, rule: ResponseRule, email: EmailMessage) -> bool:
        """Check if a rule matches the given email"""
        try:
            if not rule.trigger_patterns:
                return False
            
            email_text = f"{email.subject or ''} {email.body_text or ''}".lower()
            
            # Check trigger patterns
            for pattern in rule.trigger_patterns:
                if isinstance(pattern, str):
                    if pattern.lower() in email_text:
                        return True
                elif isinstance(pattern, dict):
                    # Handle regex patterns
                    if pattern.get('type') == 'regex':
                        try:
                            if re.search(pattern['pattern'], email_text, re.IGNORECASE):
                                return True
                        except:
                            continue
            
            # Check trigger keywords
            if rule.trigger_keywords:
                for keyword in rule.trigger_keywords:
                    if keyword.lower() in email_text:
                        return True
            
            # Check subject patterns
            if rule.subject_patterns and email.subject:
                for pattern in rule.subject_patterns:
                    if pattern.lower() in email.subject.lower():
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rule match: {e}")
            return False

    def _determine_generation_strategy(self, 
                                     email: EmailMessage,
                                     user_profile: Optional[WritingStyleProfile],
                                     client_info: Optional[Client],
                                     applicable_rules: List[ResponseRule],
                                     options: Optional[Dict]) -> str:
        """Determine the best generation strategy"""
        try:
            # Force strategy if specified in options
            if options and options.get('strategy'):
                return options['strategy']
            
            # Rule-based if high-confidence rules exist
            if applicable_rules:
                top_rule = applicable_rules[0]
                if top_rule.success_rate and top_rule.success_rate > 0.8:
                    return "rule_based"
            
            # RAG if we have sufficient context and user profile
            if user_profile and user_profile.confidence_score and user_profile.confidence_score > 0.7:
                return "rag_only"
            
            # Hybrid if we have both rules and some context
            if applicable_rules and user_profile:
                return "hybrid"
            
            # Fallback to templates
            return "template_fallback"
            
        except Exception as e:
            logger.error(f"Error determining strategy: {e}")
            return "template_fallback"

    async def _generate_rule_based_response(self, 
                                          email: EmailMessage,
                                          user_profile: Optional[WritingStyleProfile],
                                          rule: ResponseRule,
                                          start_time: datetime) -> ResponseGenerationResult:
        """Generate response using rule templates"""
        try:
            # Apply rule template
            response_text = await self._apply_rule_template(rule, email, user_profile)
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ResponseGenerationResult(
                response_text=response_text,
                response_type="template",
                confidence_score=rule.success_rate or 0.8,
                relevance_score=0.9,  # High relevance since rule matched
                style_match_score=0.7,  # Will be adjusted in style matching
                generation_time_ms=processing_time,
                model_used="rule_template",
                tokens_used=len(response_text.split()),
                context_sources=[],
                rule_applied=rule.rule_name
            )
            
        except Exception as e:
            logger.error(f"Error generating rule-based response: {e}")
            raise

    async def _generate_rag_response(self, 
                                   email: EmailMessage,
                                   user_id: str,
                                   user_profile: Optional[WritingStyleProfile],
                                   start_time: datetime) -> ResponseGenerationResult:
        """Generate response using RAG"""
        try:
            # Use RAG engine
            rag_result = await self.rag_engine.generate_context_aware_response(
                incoming_email=email,
                user_id=user_id,
                writing_style=user_profile,
                max_context_length=2000
            )
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ResponseGenerationResult(
                response_text=rag_result["response_text"],
                response_type="rag",
                confidence_score=rag_result["confidence_score"],
                relevance_score=0.8,  # Will be calculated based on context
                style_match_score=rag_result.get("style_match_applied", False) and 0.9 or 0.5,
                generation_time_ms=processing_time,
                model_used=rag_result["generation_metadata"].get("model_used", "unknown"),
                tokens_used=len(rag_result["response_text"].split()),
                context_sources=rag_result["context_sources"]
            )
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            raise

    async def _generate_hybrid_response(self, 
                                      email: EmailMessage,
                                      user_id: str,
                                      user_profile: Optional[WritingStyleProfile],
                                      rules: List[ResponseRule],
                                      start_time: datetime) -> ResponseGenerationResult:
        """Generate response using both RAG and rules"""
        try:
            # Get RAG response
            rag_result = await self.rag_engine.generate_context_aware_response(
                incoming_email=email,
                user_id=user_id,
                writing_style=user_profile,
                max_context_length=1500  # Leave room for rule content
            )
            
            # Apply best matching rule as enhancement
            best_rule = rules[0] if rules else None
            if best_rule:
                # Enhance RAG response with rule elements
                enhanced_response = await self._enhance_response_with_rule(
                    rag_result["response_text"], best_rule, email
                )
            else:
                enhanced_response = rag_result["response_text"]
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ResponseGenerationResult(
                response_text=enhanced_response,
                response_type="hybrid",
                confidence_score=(rag_result["confidence_score"] + 0.8) / 2,  # Average with rule confidence
                relevance_score=0.85,
                style_match_score=rag_result.get("style_match_applied", False) and 0.9 or 0.6,
                generation_time_ms=processing_time,
                model_used=f"hybrid_{rag_result['generation_metadata'].get('model_used', 'unknown')}",
                tokens_used=len(enhanced_response.split()),
                context_sources=rag_result["context_sources"],
                rule_applied=best_rule.rule_name if best_rule else None
            )
            
        except Exception as e:
            logger.error(f"Error generating hybrid response: {e}")
            raise

    async def _generate_template_response(self, 
                                        email: EmailMessage,
                                        user_profile: Optional[WritingStyleProfile],
                                        client_info: Optional[Client],
                                        start_time: datetime) -> ResponseGenerationResult:
        """Generate response using basic templates"""
        try:
            # Determine response type based on email content
            response_templates = self._get_response_templates()
            
            email_text = f"{email.subject or ''} {email.body_text or ''}".lower()
            
            # Select appropriate template
            template = self._select_template(email_text, response_templates)
            
            # Fill template variables
            response_text = await self._fill_template_variables(
                template, email, user_profile, client_info
            )
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ResponseGenerationResult(
                response_text=response_text,
                response_type="template",
                confidence_score=0.6,
                relevance_score=0.7,
                style_match_score=0.5,  # Will be improved by style matching
                generation_time_ms=processing_time,
                model_used="template_engine",
                tokens_used=len(response_text.split()),
                context_sources=[]
            )
            
        except Exception as e:
            logger.error(f"Error generating template response: {e}")
            raise

    async def _apply_rule_template(self, 
                                 rule: ResponseRule,
                                 email: EmailMessage,
                                 user_profile: Optional[WritingStyleProfile]) -> str:
        """Apply rule template with variable substitution"""
        try:
            template = rule.response_template
            variables = rule.response_variables or {}
            
            # Standard variables
            standard_vars = {
                'sender_name': self._extract_sender_name(email.sender),
                'subject': email.subject or 'your message',
                'date': datetime.now().strftime('%B %d, %Y'),
                'user_name': user_profile and getattr(user_profile, 'user_name', 'AI Assistant') or 'AI Assistant'
            }
            
            # Merge variables
            all_vars = {**standard_vars, **variables}
            
            # Replace variables in template
            response = template
            for var, value in all_vars.items():
                response = response.replace(f'{{{var}}}', str(value))
            
            return response
            
        except Exception as e:
            logger.error(f"Error applying rule template: {e}")
            return rule.response_template

    async def _enhance_response_with_rule(self, 
                                        rag_response: str,
                                        rule: ResponseRule,
                                        email: EmailMessage) -> str:
        """Enhance RAG response with rule elements"""
        try:
            # Add rule-specific elements based on rule category
            if rule.rule_category == "closing":
                # Add specific closing from rule
                if rule.response_template:
                    closing = rule.response_template.strip()
                    return f"{rag_response}\n\n{closing}"
            
            elif rule.rule_category == "auto_reply":
                # Prepend auto-reply elements
                if rule.response_template:
                    auto_reply = rule.response_template.strip()
                    return f"{auto_reply}\n\n{rag_response}"
            
            elif rule.rule_category == "signature":
                # Add signature
                if rule.response_template:
                    signature = rule.response_template.strip()
                    return f"{rag_response}\n\n{signature}"
            
            return rag_response
            
        except Exception as e:
            logger.error(f"Error enhancing response with rule: {e}")
            return rag_response

    def _get_response_templates(self) -> Dict[str, str]:
        """Get basic response templates"""
        return {
            "acknowledgment": "Thank you for your email regarding '{subject}'. I have received your message and will review it carefully.",
            "meeting_request": "Thank you for your meeting request. I will check my calendar and get back to you with available times.",
            "information_request": "Thank you for your inquiry. I will gather the requested information and provide you with a comprehensive response.",
            "follow_up": "Thank you for following up on this matter. I will prioritize this and get back to you soon.",
            "urgent": "I understand this is urgent. I am reviewing your message now and will respond as quickly as possible.",
            "generic": "Thank you for your email. I will review your message and get back to you shortly."
        }

    def _select_template(self, email_text: str, templates: Dict[str, str]) -> str:
        """Select most appropriate template based on email content"""
        try:
            # Keywords for different template types
            template_keywords = {
                "meeting_request": ["meeting", "call", "schedule", "appointment", "available"],
                "information_request": ["information", "details", "question", "inquiry", "clarification"],
                "follow_up": ["follow", "following up", "checking", "status", "update"],
                "urgent": ["urgent", "asap", "immediately", "emergency", "critical"]
            }
            
            # Score templates
            template_scores = {}
            for template_type, keywords in template_keywords.items():
                score = sum(1 for keyword in keywords if keyword in email_text)
                if score > 0:
                    template_scores[template_type] = score
            
            # Select best template
            if template_scores:
                best_template = max(template_scores, key=template_scores.get)
                return templates[best_template]
            else:
                return templates["generic"]
                
        except Exception as e:
            logger.error(f"Error selecting template: {e}")
            return templates["generic"]

    async def _fill_template_variables(self, 
                                     template: str,
                                     email: EmailMessage,
                                     user_profile: Optional[WritingStyleProfile],
                                     client_info: Optional[Client]) -> str:
        """Fill template variables"""
        try:
            variables = {
                'subject': email.subject or 'your message',
                'sender_name': self._extract_sender_name(email.sender),
                'client_name': client_info.client_name if client_info else 'valued client',
                'date': datetime.now().strftime('%B %d, %Y')
            }
            
            response = template
            for var, value in variables.items():
                response = response.replace(f'{{{var}}}', str(value))
            
            return response
            
        except Exception as e:
            logger.error(f"Error filling template variables: {e}")
            return template

    async def _apply_style_matching(self, 
                                  result: ResponseGenerationResult,
                                  user_profile: Optional[WritingStyleProfile]) -> ResponseGenerationResult:
        """Apply user's writing style to generated response"""
        try:
            if not user_profile:
                return result
            
            response = result.response_text
            
            # Apply formality level
            if user_profile.formality_score:
                if user_profile.formality_score > 0.8:
                    # Make more formal
                    response = self._make_more_formal(response)
                elif user_profile.formality_score < 0.3:
                    # Make more casual
                    response = self._make_more_casual(response)
            
            # Apply common phrases
            if user_profile.common_phrases:
                response = self._incorporate_common_phrases(response, user_profile.common_phrases)
            
            # Apply closing patterns
            if user_profile.closing_patterns:
                response = self._apply_closing_pattern(response, user_profile.closing_patterns[0])
            
            # Update style match score
            result.response_text = response
            result.style_match_score = min(1.0, result.style_match_score + 0.2)
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying style matching: {e}")
            return result

    def _make_more_formal(self, text: str) -> str:
        """Make text more formal"""
        replacements = {
            "thanks": "thank you",
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "i'll": "I will",
            "we'll": "we will"
        }
        
        for informal, formal in replacements.items():
            text = text.replace(informal, formal)
        
        return text

    def _make_more_casual(self, text: str) -> str:
        """Make text more casual"""
        replacements = {
            "thank you very much": "thanks",
            "I would appreciate": "I'd appreciate",
            "I will": "I'll",
            "we will": "we'll"
        }
        
        for formal, casual in replacements.items():
            text = text.replace(formal, casual)
        
        return text

    def _incorporate_common_phrases(self, text: str, phrases: List[str]) -> str:
        """Incorporate user's common phrases naturally"""
        try:
            # Simple incorporation - add a common phrase if appropriate
            if phrases and "thank" in text.lower():
                common_thanks = [p for p in phrases if "thank" in p.lower()]
                if common_thanks:
                    text = text.replace("Thank you", common_thanks[0], 1)
            
            return text
            
        except Exception:
            return text

    def _apply_closing_pattern(self, text: str, closing: str) -> str:
        """Apply user's preferred closing pattern"""
        try:
            # Find and replace generic closings
            generic_closings = ["Best regards", "Sincerely", "Thank you"]
            
            for generic in generic_closings:
                if generic in text:
                    text = text.replace(generic, closing, 1)
                    break
            else:
                # Add closing if none exists
                if not any(closing_word in text.lower() for closing_word in ["regards", "sincerely", "best"]):
                    text = f"{text}\n\n{closing}"
            
            return text
            
        except Exception:
            return text

    async def _validate_response_quality(self, 
                                       result: ResponseGenerationResult,
                                       original_email: EmailMessage) -> ResponseGenerationResult:
        """Validate response quality and add metrics"""
        try:
            quality_metrics = {}
            
            # Length check
            response_length = len(result.response_text.split())
            quality_metrics["word_count"] = response_length
            quality_metrics["appropriate_length"] = 20 <= response_length <= 200
            
            # Relevance check (basic keyword matching)
            original_keywords = self._extract_keywords(original_email.body_text or "")
            response_keywords = self._extract_keywords(result.response_text)
            
            keyword_overlap = len(set(original_keywords) & set(response_keywords))
            quality_metrics["keyword_relevance"] = keyword_overlap / max(len(original_keywords), 1)
            
            # Professional tone check
            quality_metrics["professional_tone"] = self._check_professional_tone(result.response_text)
            
            # Completeness check
            quality_metrics["has_greeting"] = any(word in result.response_text.lower() 
                                                 for word in ["thank", "hello", "hi", "dear"])
            quality_metrics["has_closing"] = any(word in result.response_text.lower() 
                                                for word in ["regards", "sincerely", "best", "thanks"])
            
            # Calculate overall quality score
            quality_score = (
                (quality_metrics["appropriate_length"] and 0.2 or 0) +
                (quality_metrics["keyword_relevance"] * 0.3) +
                (quality_metrics["professional_tone"] * 0.3) +
                (quality_metrics["has_greeting"] and 0.1 or 0) +
                (quality_metrics["has_closing"] and 0.1 or 0)
            )
            
            quality_metrics["overall_quality"] = quality_score
            result.quality_metrics = quality_metrics
            
            # Adjust confidence based on quality
            result.confidence_score = (result.confidence_score + quality_score) / 2
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating response quality: {e}")
            return result

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text"""
        try:
            # Simple keyword extraction
            words = re.findall(r'\b\w{4,}\b', text.lower())
            # Filter out common words
            stop_words = {"with", "that", "this", "have", "will", "from", "they", "been", "have", "were", "said", "each", "which", "their", "time", "would", "about", "could", "there", "other", "after", "first", "never", "these", "should", "where", "being", "every", "great", "might", "shall", "still", "those", "while", "again", "before", "during", "always", "please", "thank", "email", "message"}
            keywords = [word for word in words if word not in stop_words]
            return keywords[:10]  # Return top 10
            
        except Exception:
            return []

    def _check_professional_tone(self, text: str) -> float:
        """Check if text maintains professional tone"""
        try:
            # Simple heuristics for professional tone
            unprofessional_indicators = ["lol", "omg", "wtf", "!!!!", "????"]
            professional_indicators = ["please", "thank you", "appreciate", "sincerely", "regards"]
            
            unprofessional_count = sum(1 for indicator in unprofessional_indicators if indicator in text.lower())
            professional_count = sum(1 for indicator in professional_indicators if indicator in text.lower())
            
            if unprofessional_count > 0:
                return 0.3
            elif professional_count > 0:
                return 0.9
            else:
                return 0.7  # Neutral
                
        except Exception:
            return 0.7

    async def _store_generated_response(self, 
                                      result: ResponseGenerationResult,
                                      original_email: EmailMessage,
                                      user_id: str):
        """Store generated response in database"""
        try:
            async with AsyncSessionLocal() as session:
                generated_response = GeneratedResponse(
                    original_email_id=original_email.id,
                    generated_response=result.response_text,
                    response_type=result.response_type,
                    confidence_score=result.confidence_score,
                    relevance_score=result.relevance_score,
                    style_match_score=result.style_match_score,
                    model_used=result.model_used,
                    generation_time_ms=result.generation_time_ms,
                    tokens_used=result.tokens_used,
                    retrieved_contexts=[source for source in result.context_sources],
                    context_sources=result.context_sources,
                    status="draft"
                )
                
                session.add(generated_response)
                await session.commit()
                
                logger.info(f"Stored generated response for email {original_email.id}")
                
        except Exception as e:
            logger.error(f"Error storing generated response: {e}")

    async def _generate_fallback_response(self, email: EmailMessage, error: str) -> ResponseGenerationResult:
        """Generate fallback response when generation fails"""
        fallback_text = f"Thank you for your email regarding '{email.subject or 'your message'}'. I have received your message and will get back to you soon."
        
        return ResponseGenerationResult(
            response_text=fallback_text,
            response_type="fallback",
            confidence_score=0.3,
            relevance_score=0.5,
            style_match_score=0.4,
            generation_time_ms=0,
            model_used="fallback",
            tokens_used=len(fallback_text.split()),
            context_sources=[],
            quality_metrics={"error": error}
        )

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
            
        except Exception:
            return None

    def _extract_sender_name(self, sender: str) -> str:
        """Extract sender name from email string"""
        try:
            if not sender:
                return "there"
            
            # Extract name from "Name <email@domain.com>" format
            name_match = re.search(r'^([^<]+)<', sender)
            if name_match:
                name = name_match.group(1).strip().strip('"')
                return name if name else "there"
            
            # If just email, extract name part
            if '@' in sender:
                name_part = sender.split('@')[0]
                return name_part.replace('.', ' ').replace('_', ' ').title()
            
            return sender
            
        except Exception:
            return "there"