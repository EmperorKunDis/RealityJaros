from typing import List, Dict, Optional, Any, Tuple
import logging
from datetime import datetime
import json
import asyncio

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableMap

from src.services.vector_db_manager import VectorDatabaseManager
from src.models.response import WritingStyleProfile
from src.models.email import EmailMessage
from src.config.settings import settings
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Advanced Retrieval-Augmented Generation engine
    Orchestrates context retrieval and response generation
    """
    
    def __init__(self, vector_db_manager: VectorDatabaseManager):
        self.vector_db_manager = vector_db_manager
        self.llm = self._initialize_llm()
        self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        self.qa_chains = {}
        self.memories = {}
        
    def _initialize_llm(self):
        """Initialize the language model"""
        try:
            if settings.openai_api_key:
                return ChatOpenAI(
                    model_name=settings.openai_model,
                    temperature=0.7,
                    max_tokens=500,
                    openai_api_key=settings.openai_api_key
                )
            else:
                logger.warning("OpenAI API key not configured, using mock LLM")
                return None  # Mock for development
                
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            return None

    async def initialize_qa_chains(self, user_id: str):
        """
        Initialize QA chains for user-specific collections
        
        Args:
            user_id: User identifier
        """
        try:
            # Get collection statistics
            collection_stats = await self.vector_db_manager.get_collection_stats()
            
            # Initialize chains for user's collections
            user_collections = [
                name for name in collection_stats.keys() 
                if name.startswith(f"user_{user_id}_") or name == "user_emails_general"
            ]
            
            for collection_name in user_collections:
                if collection_stats[collection_name]["document_count"] > 0:
                    await self._create_qa_chain(user_id, collection_name)
            
            logger.info(f"Initialized QA chains for {len(self.qa_chains)} collections")
            
        except Exception as e:
            logger.error(f"Error initializing QA chains: {e}")

    async def _create_qa_chain(self, user_id: str, collection_name: str):
        """
        Create a QA chain for a specific collection
        
        Args:
            user_id: User identifier
            collection_name: Collection name
        """
        try:
            if not self.llm:
                logger.warning("LLM not available, skipping QA chain creation")
                return
            
            # Create memory for conversation history
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            # Create custom prompt template
            prompt_template = self._create_prompt_template(user_id)
            
            # Create QA chain (simplified for now since we don't have direct LangChain-ChromaDB integration)
            chain_key = f"{user_id}_{collection_name}"
            self.qa_chains[chain_key] = {
                "collection_name": collection_name,
                "memory": memory,
                "prompt_template": prompt_template,
                "user_id": user_id
            }
            
            logger.info(f"Created QA chain for collection '{collection_name}'")
            
        except Exception as e:
            logger.error(f"Error creating QA chain: {e}")

    def _create_prompt_template(self, user_id: str) -> PromptTemplate:
        """
        Create a custom prompt template for the user
        
        Args:
            user_id: User identifier
            
        Returns:
            Prompt template
        """
        template = """You are an AI email assistant helping to generate appropriate email responses. 
        Use the following context from previous emails to inform your response.

        Context from previous emails:
        {context}

        Current email to respond to:
        {question}

        Writing style guidelines:
        {style_guidelines}

        Generate a professional email response that:
        1. Addresses the main points in the current email
        2. Matches the user's writing style and tone
        3. Is contextually appropriate based on the email history
        4. Is concise and actionable

        Response:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question", "style_guidelines"]
        )

    async def generate_context_aware_response(self, 
                                            incoming_email: EmailMessage,
                                            user_id: str,
                                            writing_style: Optional[WritingStyleProfile] = None,
                                            max_context_length: int = 2000) -> Dict[str, Any]:
        """
        Generate response using relevant context and style matching
        
        Args:
            incoming_email: The email to respond to
            user_id: User identifier
            writing_style: User's writing style profile
            max_context_length: Maximum context length
            
        Returns:
            Generated response with metadata
        """
        try:
            logger.info(f"Generating context-aware response for email {incoming_email.id}")
            
            # Retrieve relevant context
            context_results = await self.retrieve_relevant_context(
                incoming_email, user_id, max_context_length
            )
            
            # Build context string
            context_text = self._build_context_text(context_results)
            
            # Get style guidelines
            style_guidelines = self._build_style_guidelines(writing_style)
            
            # Prepare the email content for processing
            email_content = self._format_email_for_processing(incoming_email)
            
            # Generate response
            if self.llm:
                response_text = await self._generate_llm_response(
                    email_content, context_text, style_guidelines, user_id
                )
            else:
                # Mock response for development
                response_text = self._generate_mock_response(incoming_email, context_results)
            
            # Calculate confidence score
            confidence_score = self._calculate_response_confidence(
                context_results, len(response_text)
            )
            
            return {
                "response_text": response_text,
                "confidence_score": confidence_score,
                "context_sources": [
                    {
                        "source": result["metadata"].get("email_id", "unknown"),
                        "relevance": result["similarity"],
                        "snippet": result["document"][:100] + "..."
                    }
                    for result in context_results[:5]
                ],
                "context_count": len(context_results),
                "style_match_applied": writing_style is not None,
                "generation_metadata": {
                    "model_used": settings.openai_model if self.llm else "mock",
                    "max_context_length": max_context_length,
                    "actual_context_length": len(context_text)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating context-aware response: {e}")
            return {
                "response_text": "I apologize, but I'm unable to generate a response at this time. Please try again later.",
                "confidence_score": 0.0,
                "context_sources": [],
                "context_count": 0,
                "style_match_applied": False,
                "error": str(e)
            }

    async def retrieve_relevant_context(self, 
                                      incoming_email: EmailMessage,
                                      user_id: str, 
                                      max_context_length: int = 2000) -> List[Dict]:
        """
        Retrieve most relevant email contexts for the incoming email
        
        Args:
            incoming_email: Email to find context for
            user_id: User identifier
            max_context_length: Maximum total context length
            
        Returns:
            List of relevant context documents
        """
        try:
            # Create search query from email content
            search_query = self._create_search_query(incoming_email)
            
            # Determine collections to search
            collection_names = [f"user_{user_id}_emails", "user_emails_general"]
            
            # Perform similarity search
            search_results = await self.vector_db_manager.similarity_search(
                query=search_query,
                collection_names=collection_names,
                k=10,  # Get more results initially
                user_id=user_id
            )
            
            # Filter and rank results
            filtered_results = await self._filter_and_rank_results(
                search_results, incoming_email, user_id
            )
            
            # Trim to context length limit
            final_results = self._trim_to_context_limit(filtered_results, max_context_length)
            
            logger.info(f"Retrieved {len(final_results)} relevant context documents")
            return final_results
            
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return []

    def _create_search_query(self, email: EmailMessage) -> str:
        """
        Create search query from email content
        
        Args:
            email: Email message
            
        Returns:
            Search query string
        """
        try:
            query_parts = []
            
            # Add subject
            if email.subject:
                query_parts.append(email.subject)
            
            # Add key phrases from body
            if email.body_text:
                # Simple extraction of key phrases
                words = email.body_text.split()
                if len(words) > 50:
                    # Use first 50 words as query
                    query_parts.append(" ".join(words[:50]))
                else:
                    query_parts.append(email.body_text)
            
            return " ".join(query_parts)
            
        except Exception as e:
            logger.error(f"Error creating search query: {e}")
            return email.subject or "email response"

    async def _filter_and_rank_results(self, 
                                     search_results: List[Dict],
                                     incoming_email: EmailMessage,
                                     user_id: str) -> List[Dict]:
        """
        Filter and rank search results for relevance
        
        Args:
            search_results: Raw search results
            incoming_email: Email being responded to
            user_id: User identifier
            
        Returns:
            Filtered and ranked results
        """
        try:
            filtered_results = []
            
            for result in search_results:
                # Skip results with very low similarity
                if result["similarity"] < 0.3:
                    continue
                
                # Skip the same email (if it exists in vector DB)
                if result["metadata"].get("email_id") == str(incoming_email.id):
                    continue
                
                # Prefer outgoing emails (user's responses) for style learning
                if result["metadata"].get("direction") == "outgoing":
                    result["relevance_boost"] = 0.1
                else:
                    result["relevance_boost"] = 0.0
                
                # Boost recent emails
                email_date = result["metadata"].get("sent_date")
                if email_date:
                    try:
                        date_obj = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                        days_old = (datetime.utcnow() - date_obj.replace(tzinfo=None)).days
                        if days_old < 30:
                            result["relevance_boost"] += 0.05
                    except:
                        pass
                
                # Calculate final relevance score
                result["final_relevance"] = result["similarity"] + result["relevance_boost"]
                filtered_results.append(result)
            
            # Sort by final relevance
            filtered_results.sort(key=lambda x: x["final_relevance"], reverse=True)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error filtering and ranking results: {e}")
            return search_results

    def _trim_to_context_limit(self, results: List[Dict], max_length: int) -> List[Dict]:
        """
        Trim results to fit within context length limit
        
        Args:
            results: Search results
            max_length: Maximum total character length
            
        Returns:
            Trimmed results
        """
        try:
            trimmed_results = []
            total_length = 0
            
            for result in results:
                doc_length = len(result["document"])
                if total_length + doc_length <= max_length:
                    trimmed_results.append(result)
                    total_length += doc_length
                else:
                    # Try to fit a truncated version
                    remaining_space = max_length - total_length
                    if remaining_space > 100:  # Only if we have meaningful space
                        truncated_result = result.copy()
                        truncated_result["document"] = result["document"][:remaining_space]
                        trimmed_results.append(truncated_result)
                    break
            
            return trimmed_results
            
        except Exception as e:
            logger.error(f"Error trimming context: {e}")
            return results[:5]  # Fallback to first 5 results

    def _build_context_text(self, context_results: List[Dict]) -> str:
        """
        Build context text from search results
        
        Args:
            context_results: Context documents
            
        Returns:
            Formatted context text
        """
        try:
            if not context_results:
                return "No relevant context found."
            
            context_parts = []
            for i, result in enumerate(context_results, 1):
                metadata = result["metadata"]
                direction = metadata.get("direction", "unknown")
                sender = metadata.get("sender", "unknown")
                subject = metadata.get("subject", "No subject")
                
                context_part = f"Context {i} ({direction} email):\n"
                context_part += f"From: {sender}\n"
                context_part += f"Subject: {subject}\n"
                context_part += f"Content: {result['document']}\n"
                context_part += f"Relevance: {result['similarity']:.2f}\n\n"
                
                context_parts.append(context_part)
            
            return "".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building context text: {e}")
            return "Context processing error."

    def _build_style_guidelines(self, writing_style: Optional[WritingStyleProfile]) -> str:
        """
        Build style guidelines from writing style profile
        
        Args:
            writing_style: User's writing style profile
            
        Returns:
            Style guidelines text
        """
        try:
            if not writing_style:
                return "Use a professional, clear communication style."
            
            guidelines = []
            
            # Formality level
            if writing_style.formality_score:
                if writing_style.formality_score > 0.7:
                    guidelines.append("Use formal language and professional tone.")
                elif writing_style.formality_score < 0.3:
                    guidelines.append("Use casual, friendly language.")
                else:
                    guidelines.append("Use semi-formal, approachable language.")
            
            # Sentence length
            if writing_style.avg_sentence_length:
                if writing_style.avg_sentence_length > 20:
                    guidelines.append("Use longer, detailed sentences.")
                else:
                    guidelines.append("Keep sentences concise and clear.")
            
            # Common phrases
            if writing_style.common_phrases:
                phrases = writing_style.common_phrases[:3]  # Top 3 phrases
                guidelines.append(f"Consider using phrases like: {', '.join(phrases)}")
            
            # Closing patterns
            if writing_style.closing_patterns:
                closing = writing_style.closing_patterns[0]  # Most common closing
                guidelines.append(f"End with something like: '{closing}'")
            
            # Bullet points preference
            if writing_style.use_bullet_points:
                guidelines.append("Use bullet points when listing items.")
            
            return ". ".join(guidelines) + "."
            
        except Exception as e:
            logger.error(f"Error building style guidelines: {e}")
            return "Use a professional, clear communication style."

    def _format_email_for_processing(self, email: EmailMessage) -> str:
        """
        Format email for LLM processing
        
        Args:
            email: Email message
            
        Returns:
            Formatted email text
        """
        try:
            formatted = f"Subject: {email.subject or 'No subject'}\n"
            formatted += f"From: {email.sender}\n"
            formatted += f"Date: {email.sent_datetime}\n\n"
            formatted += f"Message:\n{email.body_text or 'No content'}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting email: {e}")
            return f"Email content: {email.body_text or 'No content'}"

    async def _generate_llm_response(self, 
                                   email_content: str,
                                   context_text: str,
                                   style_guidelines: str,
                                   user_id: str) -> str:
        """
        Generate response using LLM
        
        Args:
            email_content: Formatted email content
            context_text: Context from previous emails
            style_guidelines: Style guidelines
            user_id: User identifier
            
        Returns:
            Generated response text
        """
        try:
            if not self.llm:
                return self._generate_mock_response_from_content(email_content)
            
            # Get prompt template
            chain_key = f"{user_id}_general"
            if chain_key in self.qa_chains:
                prompt_template = self.qa_chains[chain_key]["prompt_template"]
            else:
                prompt_template = self._create_prompt_template(user_id)
            
            # Format prompt
            prompt = prompt_template.format(
                context=context_text,
                question=email_content,
                style_guidelines=style_guidelines
            )
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.predict(prompt)
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._generate_mock_response_from_content(email_content)

    def _generate_mock_response(self, email: EmailMessage, context_results: List[Dict]) -> str:
        """Generate mock response for development"""
        return f"""Thank you for your email regarding "{email.subject or 'your message'}".

I've reviewed your message and will get back to you with a detailed response shortly. 

Based on our previous communications, I understand this is important and will prioritize accordingly.

Best regards"""

    def _generate_mock_response_from_content(self, email_content: str) -> str:
        """Generate mock response from email content"""
        return f"""Thank you for your email.

I've received your message and will review it carefully. I'll get back to you with a response soon.

If this is urgent, please feel free to call me directly.

Best regards"""

    def _calculate_response_confidence(self, context_results: List[Dict], response_length: int) -> float:
        """
        Calculate confidence score for the generated response
        
        Args:
            context_results: Context used for generation
            response_length: Length of generated response
            
        Returns:
            Confidence score (0-1)
        """
        try:
            confidence = 0.5  # Base confidence
            
            # Boost confidence based on context quality
            if context_results:
                avg_similarity = sum(r["similarity"] for r in context_results) / len(context_results)
                confidence += avg_similarity * 0.3
            
            # Boost confidence based on context quantity
            context_boost = min(len(context_results) * 0.05, 0.2)
            confidence += context_boost
            
            # Adjust based on response length (reasonable length = higher confidence)
            if 50 <= response_length <= 500:
                confidence += 0.1
            elif response_length < 20:
                confidence -= 0.2
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5

    async def update_conversation_memory(self, user_id: str, query: str, response: str):
        """
        Update conversation memory with new interaction
        
        Args:
            user_id: User identifier
            query: Original query/email
            response: Generated response
        """
        try:
            # Update memory for user's chains
            for chain_key, chain_data in self.qa_chains.items():
                if chain_data["user_id"] == user_id:
                    memory = chain_data["memory"]
                    memory.save_context(
                        {"input": query},
                        {"output": response}
                    )
            
        except Exception as e:
            logger.error(f"Error updating conversation memory: {e}")

    async def get_conversation_history(self, user_id: str) -> List[Dict]:
        """
        Get conversation history for user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation history
        """
        try:
            # Get memory from user's primary chain
            chain_key = f"{user_id}_general"
            if chain_key in self.qa_chains:
                memory = self.qa_chains[chain_key]["memory"]
                return memory.chat_memory.messages
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []