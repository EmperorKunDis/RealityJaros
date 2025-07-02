"""
Ultimate Prompt Generation Service

Implements dynamic, user-profile-based prompt creation as specified in the
Ultimate AI Email Agent design. Creates personalized prompts based on:
- User's writing style analysis
- Correspondence group categorization  
- Communication context and history
- Response quality feedback loop
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import AsyncSessionLocal
from src.models.user import User
from src.models.email import EmailMessage
from src.models.client import Client
from src.models.response import GeneratedResponse
from src.models.setup_wizard import (
    WritingStyleConfiguration,
    ClientCategoryConfiguration,
    EmailPreferences
)

logger = logging.getLogger(__name__)


class UltimatePromptService:
    """
    Service for generating ultimate prompts based on user profile and context
    Implements the "ultimativní prompt" concept from the Czech design document
    """
    
    def __init__(self):
        self.base_prompts = self._load_base_prompt_templates()
        self.style_modifiers = self._load_style_modifiers()
        self.context_enhancers = self._load_context_enhancers()
    
    async def generate_ultimate_prompt(
        self, 
        user_id: str, 
        email_context: Optional[Dict[str, Any]] = None,
        correspondence_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate the ultimate prompt for a user based on their profile and context
        """
        try:
            async with AsyncSessionLocal() as session:
                # Get comprehensive user profile
                user_profile = await self._get_comprehensive_user_profile(user_id, session)
                
                # Analyze recent communication patterns
                communication_analysis = await self._analyze_recent_communications(user_id, session)
                
                # Get correspondence group specific context
                group_context = await self._get_correspondence_group_context(
                    user_id, correspondence_group, session
                )
                
                # Generate base prompt structure
                base_prompt = self._generate_base_prompt_structure(user_profile)
                
                # Apply writing style modifications
                styled_prompt = self._apply_writing_style(base_prompt, user_profile)
                
                # Add context-specific enhancements
                contextualized_prompt = self._add_context_enhancements(
                    styled_prompt, 
                    email_context, 
                    group_context,
                    communication_analysis
                )
                
                # Apply personalization layers
                personalized_prompt = self._apply_personalization_layers(
                    contextualized_prompt, 
                    user_profile,
                    communication_analysis
                )
                
                # Generate final optimized prompt
                ultimate_prompt = self._finalize_ultimate_prompt(
                    personalized_prompt,
                    user_profile,
                    email_context
                )
                
                # Store prompt for analysis and improvement
                await self._store_prompt_analytics(
                    user_id, 
                    ultimate_prompt,
                    email_context,
                    session
                )
                
                return {
                    "ultimate_prompt": ultimate_prompt["content"],
                    "prompt_metadata": ultimate_prompt["metadata"],
                    "confidence_score": ultimate_prompt["confidence_score"],
                    "personalization_level": ultimate_prompt["personalization_level"],
                    "generated_at": datetime.utcnow().isoformat(),
                    "version": "1.0",
                    "user_id": user_id
                }
                
        except Exception as e:
            logger.error(f"Error generating ultimate prompt for user {user_id}: {str(e)}")
            raise
    
    async def _get_comprehensive_user_profile(self, user_id: str, session: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive user profile including all configuration data"""
        try:
            # Get user basic info
            user_stmt = select(User).where(User.id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get writing style configuration
            style_stmt = select(WritingStyleConfiguration).where(
                WritingStyleConfiguration.user_id == user_id
            )
            style_result = await session.execute(style_stmt)
            writing_style = style_result.scalar_one_or_none()
            
            # Get email preferences
            prefs_stmt = select(EmailPreferences).where(
                EmailPreferences.user_id == user_id
            )
            prefs_result = await session.execute(prefs_stmt)
            email_prefs = prefs_result.scalar_one_or_none()
            
            # Get client categories
            categories_stmt = select(ClientCategoryConfiguration).where(
                ClientCategoryConfiguration.user_id == user_id
            )
            categories_result = await session.execute(categories_stmt)
            client_categories = categories_result.scalars().all()
            
            return {
                "user": user,
                "writing_style": writing_style,
                "email_preferences": email_prefs,
                "client_categories": client_categories,
                "languages": email_prefs.preferred_languages if email_prefs else ["cs", "en"],
                "timezone": email_prefs.timezone if email_prefs else "Europe/Prague"
            }
            
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {str(e)}")
            raise
    
    async def _analyze_recent_communications(self, user_id: str, session: AsyncSession) -> Dict[str, Any]:
        """Analyze recent communication patterns for prompt optimization"""
        try:
            # Get recent emails (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_emails_stmt = select(EmailMessage).where(
                and_(
                    EmailMessage.user_id == user_id,
                    EmailMessage.timestamp >= thirty_days_ago
                )
            ).order_by(EmailMessage.timestamp.desc()).limit(100)
            
            recent_emails_result = await session.execute(recent_emails_stmt)
            recent_emails = recent_emails_result.scalars().all()
            
            # Get recent responses
            recent_responses_stmt = select(GeneratedResponse).where(
                and_(
                    GeneratedResponse.user_id == user_id,
                    GeneratedResponse.created_at >= thirty_days_ago
                )
            ).order_by(GeneratedResponse.created_at.desc()).limit(50)
            
            recent_responses_result = await session.execute(recent_responses_stmt)
            recent_responses = recent_responses_result.scalars().all()
            
            # Analyze patterns
            analysis = {
                "total_emails": len(recent_emails),
                "incoming_emails": len([e for e in recent_emails if e.direction == "incoming"]),
                "outgoing_emails": len([e for e in recent_emails if e.direction == "outgoing"]),
                "total_responses": len(recent_responses),
                "auto_responses": len([r for r in recent_responses if r.is_auto_generated]),
                "avg_response_time": self._calculate_avg_response_time(recent_emails, recent_responses),
                "common_topics": self._extract_common_topics(recent_emails),
                "frequent_contacts": self._get_frequent_contacts(recent_emails),
                "response_success_rate": self._calculate_response_success_rate(recent_responses),
                "preferred_response_length": self._analyze_response_length_preference(recent_responses)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing recent communications for {user_id}: {str(e)}")
            return {}
    
    async def _get_correspondence_group_context(
        self, 
        user_id: str, 
        correspondence_group: Optional[str], 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get context specific to correspondence group"""
        if not correspondence_group:
            return {}
        
        try:
            # Get group configuration
            group_stmt = select(ClientCategoryConfiguration).where(
                and_(
                    ClientCategoryConfiguration.user_id == user_id,
                    ClientCategoryConfiguration.category_name == correspondence_group
                )
            )
            group_result = await session.execute(group_stmt)
            group_config = group_result.scalar_one_or_none()
            
            if not group_config:
                return {}
            
            return {
                "group_name": correspondence_group,
                "formality_level": group_config.formality_level,
                "response_template": group_config.response_template,
                "priority_level": group_config.priority_level,
                "domain_patterns": group_config.domain_patterns,
                "response_delay": group_config.response_delay_minutes
            }
            
        except Exception as e:
            logger.error(f"Error getting correspondence group context: {str(e)}")
            return {}
    
    def _generate_base_prompt_structure(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate base prompt structure"""
        user = user_profile["user"]
        languages = user_profile["languages"]
        
        # Select base template based on primary language
        primary_lang = languages[0] if languages else "cs"
        base_template = self.base_prompts.get(primary_lang, self.base_prompts["cs"])
        
        return {
            "structure": base_template,
            "language": primary_lang,
            "multilingual": len(languages) > 1,
            "supported_languages": languages,
            "user_context": {
                "name": user.display_name or "Uživatel",
                "email": user.email,
                "timezone": user_profile["timezone"]
            }
        }
    
    def _apply_writing_style(self, base_prompt: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Apply user's writing style to the prompt"""
        writing_style = user_profile["writing_style"]
        
        if not writing_style:
            return base_prompt
        
        style_modifications = {
            "formality": writing_style.formality_level,
            "tone": writing_style.tone,
            "verbosity": writing_style.verbosity,
            "signature_style": writing_style.signature_style,
            "greeting_style": writing_style.greeting_style,
            "technical_terms": writing_style.use_technical_terms,
            "emojis": writing_style.use_emojis,
            "abbreviations": writing_style.use_abbreviations
        }
        
        # Apply style modifiers
        modified_prompt = base_prompt.copy()
        modified_prompt["style_modifiers"] = style_modifications
        
        # Update prompt content based on style
        if writing_style.formality_level == "formal":
            modified_prompt["structure"] += self.style_modifiers["formal_additions"]
        elif writing_style.formality_level == "casual":
            modified_prompt["structure"] += self.style_modifiers["casual_additions"]
        
        if writing_style.verbosity == "brief":
            modified_prompt["structure"] += self.style_modifiers["brief_instructions"]
        elif writing_style.verbosity == "detailed":
            modified_prompt["structure"] += self.style_modifiers["detailed_instructions"]
        
        return modified_prompt
    
    def _add_context_enhancements(
        self, 
        prompt: Dict[str, Any], 
        email_context: Optional[Dict[str, Any]],
        group_context: Dict[str, Any],
        communication_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add context-specific enhancements to the prompt"""
        enhanced_prompt = prompt.copy()
        
        # Add email context if available
        if email_context:
            enhanced_prompt["email_context"] = {
                "subject": email_context.get("subject", ""),
                "sender": email_context.get("sender", ""),
                "urgency": email_context.get("urgency", "normal"),
                "thread_length": email_context.get("thread_length", 1)
            }
            
            # Add context-specific instructions
            if email_context.get("urgency") == "high":
                enhanced_prompt["structure"] += self.context_enhancers["urgent_response"]
            
            if email_context.get("thread_length", 1) > 3:
                enhanced_prompt["structure"] += self.context_enhancers["long_thread"]
        
        # Add correspondence group context
        if group_context:
            enhanced_prompt["group_context"] = group_context
            
            if group_context.get("formality_level") == "formal":
                enhanced_prompt["structure"] += self.context_enhancers["formal_group"]
            
            if group_context.get("priority_level") == "high":
                enhanced_prompt["structure"] += self.context_enhancers["high_priority"]
        
        # Add communication patterns
        if communication_analysis:
            enhanced_prompt["communication_patterns"] = {
                "avg_response_time": communication_analysis.get("avg_response_time", "2 hours"),
                "preferred_length": communication_analysis.get("preferred_response_length", "medium"),
                "success_rate": communication_analysis.get("response_success_rate", 0.8),
                "common_topics": communication_analysis.get("common_topics", [])
            }
        
        return enhanced_prompt
    
    def _apply_personalization_layers(
        self, 
        prompt: Dict[str, Any], 
        user_profile: Dict[str, Any],
        communication_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply deep personalization layers"""
        personalized_prompt = prompt.copy()
        
        # Add user-specific patterns
        writing_style = user_profile["writing_style"]
        if writing_style:
            personalization = {
                "signature_handling": self._get_signature_instructions(writing_style.signature_style),
                "greeting_handling": self._get_greeting_instructions(writing_style.greeting_style),
                "tone_guidance": self._get_tone_guidance(writing_style.tone),
                "urgency_detection": writing_style.response_urgency_detection
            }
            
            personalized_prompt["personalization"] = personalization
        
        # Add success pattern reinforcement
        if communication_analysis.get("response_success_rate", 0) > 0.8:
            personalized_prompt["structure"] += self.context_enhancers["successful_patterns"]
        
        return personalized_prompt
    
    def _finalize_ultimate_prompt(
        self, 
        prompt: Dict[str, Any], 
        user_profile: Dict[str, Any],
        email_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Finalize the ultimate prompt with all components"""
        
        # Build the final prompt content
        final_content = self._build_final_prompt_content(prompt, user_profile, email_context)
        
        # Calculate confidence score
        confidence_score = self._calculate_prompt_confidence(prompt, user_profile)
        
        # Determine personalization level
        personalization_level = self._calculate_personalization_level(prompt)
        
        return {
            "content": final_content,
            "metadata": {
                "components_used": list(prompt.keys()),
                "style_applied": prompt.get("style_modifiers", {}),
                "context_enhancements": len(prompt.get("email_context", {})),
                "personalization_layers": len(prompt.get("personalization", {})),
                "language": prompt.get("language", "cs"),
                "multilingual": prompt.get("multilingual", False)
            },
            "confidence_score": confidence_score,
            "personalization_level": personalization_level
        }
    
    def _build_final_prompt_content(
        self, 
        prompt: Dict[str, Any], 
        user_profile: Dict[str, Any],
        email_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the final prompt content string"""
        
        # Start with base structure
        content_parts = [prompt["structure"]]
        
        # Add user context
        user_context = prompt.get("user_context", {})
        if user_context:
            content_parts.append(f"\nKontext uživatele:")
            content_parts.append(f"- Jméno: {user_context.get('name', 'Uživatel')}")
            content_parts.append(f"- Časové pásmo: {user_context.get('timezone', 'Europe/Prague')}")
        
        # Add style instructions
        style_mods = prompt.get("style_modifiers", {})
        if style_mods:
            content_parts.append(f"\nStyl komunikace:")
            content_parts.append(f"- Formálnost: {style_mods.get('formality', 'professional')}")
            content_parts.append(f"- Tón: {style_mods.get('tone', 'friendly')}")
            content_parts.append(f"- Délka: {style_mods.get('verbosity', 'concise')}")
            
            if style_mods.get('emojis'):
                content_parts.append("- Můžeš používat emotikony, pokud je to vhodné")
            
            if style_mods.get('technical_terms'):
                content_parts.append("- Používej odborné termíny, pokud jsou relevantní")
        
        # Add email context
        email_ctx = prompt.get("email_context", {})
        if email_ctx:
            content_parts.append(f"\nKontext e-mailu:")
            if email_ctx.get("subject"):
                content_parts.append(f"- Předmět: {email_ctx['subject']}")
            if email_ctx.get("sender"):
                content_parts.append(f"- Odesílatel: {email_ctx['sender']}")
            if email_ctx.get("urgency") == "high":
                content_parts.append("- NALÉHAVOST: Vysoká - odpověz rychle a efektivně")
        
        # Add group context
        group_ctx = prompt.get("group_context", {})
        if group_ctx:
            content_parts.append(f"\nKorespondenční skupina:")
            content_parts.append(f"- Skupina: {group_ctx.get('group_name', 'Obecná')}")
            content_parts.append(f"- Úroveň formálnosti: {group_ctx.get('formality_level', 'professional')}")
            content_parts.append(f"- Priorita: {group_ctx.get('priority_level', 'normal')}")
        
        # Add personalization
        personalization = prompt.get("personalization", {})
        if personalization:
            content_parts.append(f"\nPersonalizace:")
            if personalization.get("signature_handling"):
                content_parts.append(f"- Podpis: {personalization['signature_handling']}")
            if personalization.get("greeting_handling"):
                content_parts.append(f"- Pozdrav: {personalization['greeting_handling']}")
        
        # Add final instructions
        content_parts.append(f"\nZAVĚREČNÉ INSTRUKCE:")
        content_parts.append("- Vždy reaguj v kontextu a stylu uživatele")
        content_parts.append("- Udržuj konzistentní tón během celé odpovědi")
        content_parts.append("- Buď přirozený a autentický")
        content_parts.append("- Pokud nevíš odpověď, přiznej to a navrhni řešení")
        
        return "\n".join(content_parts)
    
    def _calculate_prompt_confidence(self, prompt: Dict[str, Any], user_profile: Dict[str, Any]) -> float:
        """Calculate confidence score for the generated prompt"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on available data
        if user_profile.get("writing_style"):
            confidence += 0.2
        
        if user_profile.get("email_preferences"):
            confidence += 0.1
        
        if user_profile.get("client_categories"):
            confidence += 0.1
        
        if prompt.get("email_context"):
            confidence += 0.1
        
        if prompt.get("communication_patterns"):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_personalization_level(self, prompt: Dict[str, Any]) -> str:
        """Calculate personalization level"""
        components = len(prompt.keys())
        
        if components >= 6:
            return "high"
        elif components >= 4:
            return "medium"
        else:
            return "basic"
    
    async def _store_prompt_analytics(
        self, 
        user_id: str, 
        prompt_data: Dict[str, Any],
        email_context: Optional[Dict[str, Any]],
        session: AsyncSession
    ) -> None:
        """Store prompt analytics for improvement"""
        try:
            # This would store prompt analytics in a dedicated table
            # For now, we'll just log the analytics
            analytics = {
                "user_id": user_id,
                "prompt_length": len(prompt_data["content"]),
                "confidence_score": prompt_data["confidence_score"],
                "personalization_level": prompt_data["personalization_level"],
                "components_count": len(prompt_data["metadata"]["components_used"]),
                "has_email_context": email_context is not None,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Prompt analytics: {analytics}")
            
        except Exception as e:
            logger.error(f"Error storing prompt analytics: {str(e)}")
    
    # Helper methods for data extraction and analysis
    
    def _calculate_avg_response_time(self, emails: List, responses: List) -> str:
        """Calculate average response time"""
        # Simplified implementation
        return "2 hours"
    
    def _extract_common_topics(self, emails: List) -> List[str]:
        """Extract common topics from recent emails"""
        # Simplified implementation
        return ["work", "meetings", "projects"]
    
    def _get_frequent_contacts(self, emails: List) -> List[str]:
        """Get frequent contacts"""
        # Simplified implementation
        return ["colleague@company.com", "client@business.com"]
    
    def _calculate_response_success_rate(self, responses: List) -> float:
        """Calculate response success rate"""
        if not responses:
            return 0.8
        
        successful = sum(1 for r in responses if r.confidence_score and r.confidence_score > 0.7)
        return successful / len(responses)
    
    def _analyze_response_length_preference(self, responses: List) -> str:
        """Analyze preferred response length"""
        if not responses:
            return "medium"
        
        avg_length = sum(len(r.response_text) for r in responses if r.response_text) / len(responses)
        
        if avg_length < 200:
            return "brief"
        elif avg_length > 500:
            return "detailed"
        else:
            return "medium"
    
    def _get_signature_instructions(self, signature_style: str) -> str:
        """Get signature handling instructions"""
        mapping = {
            "minimal": "Použij minimální podpis s pouze jménem",
            "standard": "Použij standardní podpis s jménem a kontaktem",
            "detailed": "Použij detailní podpis s plnými kontaktními údaji"
        }
        return mapping.get(signature_style, mapping["standard"])
    
    def _get_greeting_instructions(self, greeting_style: str) -> str:
        """Get greeting handling instructions"""
        mapping = {
            "minimal": "Použij jednoduché pozdravy",
            "contextual": "Přizpůsob pozdrav kontextu a času",
            "formal": "Použij formální pozdravy"
        }
        return mapping.get(greeting_style, mapping["contextual"])
    
    def _get_tone_guidance(self, tone: str) -> str:
        """Get tone guidance"""
        mapping = {
            "friendly": "Buď přátelský a otevřený",
            "neutral": "Udržuj neutrální profesionální tón",
            "authoritative": "Buď autoritativní a sebevědomý"
        }
        return mapping.get(tone, mapping["friendly"])
    
    def _load_base_prompt_templates(self) -> Dict[str, str]:
        """Load base prompt templates for different languages"""
        return {
            "cs": """Jsi pokročilý AI asistent pro e-mailovou komunikaci. Tvým úkolem je pomáhat uživateli s generováním přiměřených, kontextových a personalizovaných odpovědí na e-maily.

ZÁKLADNÍ PRINCIPY:
1. Vždy zachovej styl a tón uživatele
2. Přizpůsob se kontextu a účelu e-mailu
3. Buď přesný, jasný a relevantní
4. Respektuj kulturní a jazykové preference
5. Udržuj profesionalitu dle požadavků

INSTRUKCE PRO ODPOVĚDI:
- Analyzuj příchozí e-mail a jeho kontext
- Identifikuj hlavní body, které vyžadují odpověď
- Generuj odpověď v souladu s uživatelovým stylem
- Zachovej vhodnou úroveň formálnosti
- Zkontroluj relevanci a přesnost odpovědi""",
            
            "en": """You are an advanced AI assistant for email communication. Your task is to help the user generate appropriate, contextual, and personalized email responses.

CORE PRINCIPLES:
1. Always maintain the user's style and tone
2. Adapt to the context and purpose of the email
3. Be precise, clear, and relevant
4. Respect cultural and linguistic preferences
5. Maintain professionalism as required

RESPONSE INSTRUCTIONS:
- Analyze the incoming email and its context
- Identify key points that require response
- Generate response aligned with user's style
- Maintain appropriate level of formality
- Verify relevance and accuracy of response"""
        }
    
    def _load_style_modifiers(self) -> Dict[str, str]:
        """Load style modifier templates"""
        return {
            "formal_additions": "\n- Používej formální oslovení a zakončení\n- Vyhni se zkratkám a slangem\n- Udržuj odborný slovník",
            "casual_additions": "\n- Buď přirozený a uvolněný\n- Můžeš používat zkratky a běžné výrazy\n- Udržuj přátelský tón",
            "brief_instructions": "\n- Buď stručný a přímý\n- Zaměř se na podstatné body\n- Vyhni se zbytečným detailům",
            "detailed_instructions": "\n- Poskytni podrobné informace\n- Vysvětli kontext a důvody\n- Popiš postupy a procesy"
        }
    
    def _load_context_enhancers(self) -> Dict[str, str]:
        """Load context enhancement templates"""
        return {
            "urgent_response": "\n- NALÉHAVOST: Toto je naléhavý e-mail - odpověz rychle a efektivně\n- Prioritizuj hlavní body\n- Buď jasný a přímý",
            "long_thread": "\n- DLOUHÉ VLÁKNO: Toto je součást dlouhého e-mailového vlákna\n- Referencuj předchozí body\n- Shrň klíčové informace",
            "formal_group": "\n- FORMÁLNÍ SKUPINA: Udržuj vysokou úroveň formálnosti\n- Používej oficiální jazyk\n- Dodržuj protokol",
            "high_priority": "\n- VYSOKÁ PRIORITA: Tento kontakt má vysokou prioritu\n- Věnuj zvláštní pozornost\n- Buď extra profesionální",
            "successful_patterns": "\n- ÚSPĚŠNÉ VZORY: Pokračuj ve vzorech, které se osvědčily\n- Udržuj konzistentní přístup\n- Stavěj na předchozích úspěších"
        }


# Global instance
ultimate_prompt_service = UltimatePromptService()