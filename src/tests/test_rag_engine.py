import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from src.services.rag_engine import RAGEngine
from src.services.vector_db_manager import VectorDatabaseManager
from src.models.email import EmailMessage
from src.models.response import WritingStyleProfile

@pytest.fixture
def mock_vector_manager():
    """Mock vector database manager"""
    mock = Mock(spec=VectorDatabaseManager)
    mock.search_similar_emails = AsyncMock(return_value={
        "user_emails_test_user": [
            {
                "id": "chunk_1",
                "text": "Thank you for your email. I will review it carefully.",
                "metadata": {"email_id": "email_1", "chunk_index": 0},
                "distance": 0.1
            }
        ]
    })
    mock.search_user_responses = AsyncMock(return_value=[
        {
            "id": "response_1", 
            "text": "I appreciate your message and will get back to you soon.",
            "metadata": {"response_type": "acknowledgment"},
            "distance": 0.2
        }
    ])
    return mock

@pytest.fixture
def mock_llm():
    """Mock language model"""
    mock = Mock()
    mock.invoke = Mock(return_value=Mock(content="Thank you for your email. I will review it and respond promptly."))
    return mock

@pytest.fixture
def rag_engine(mock_vector_manager):
    """RAG engine instance"""
    return RAGEngine(vector_db_manager=mock_vector_manager)

@pytest.fixture
def sample_email():
    """Sample email for testing"""
    return EmailMessage(
        id="test-email-123",
        sender="client@example.com",
        subject="Project Status Inquiry", 
        body_text="Hi, I wanted to check on the status of our project. Could you please provide an update?",
        received_at=datetime.utcnow()
    )

@pytest.fixture
def sample_writing_style():
    """Sample writing style profile"""
    return WritingStyleProfile(
        user_id="test-user-123",
        formality_score=0.7,
        common_phrases=["Thank you for reaching out", "I appreciate your patience"],
        closing_patterns=["Best regards"],
        confidence_score=0.8
    )

class TestRAGEngine:
    """Test cases for RAG Engine"""

    @pytest.mark.asyncio
    async def test_initialize_qa_chains(self, rag_engine):
        """Test QA chains initialization"""
        with patch('src.services.rag_engine.ChatOpenAI') as mock_chat, \
             patch('src.services.rag_engine.ConversationBufferMemory') as mock_memory:
            
            mock_chat.return_value = Mock()
            mock_memory.return_value = Mock()
            
            await rag_engine.initialize_qa_chains("test-user-123")
            
            assert "test-user-123" in rag_engine.qa_chains
            assert "test-user-123" in rag_engine.conversation_memories
            mock_chat.assert_called()

    @pytest.mark.asyncio
    async def test_generate_context_aware_response(self, rag_engine, sample_email, sample_writing_style, mock_vector_manager):
        """Test context-aware response generation"""
        with patch.object(rag_engine, 'initialize_qa_chains'), \
             patch.object(rag_engine, '_get_relevant_context', return_value={
                 "context_text": "Previous conversation context",
                 "sources": [{"text": "context", "metadata": {}}],
                 "total_chunks": 5
             }), \
             patch.object(rag_engine, '_generate_llm_response', return_value={
                 "response_text": "Thank you for your inquiry. I will provide an update on the project status.",
                 "model_used": "gpt-4",
                 "tokens_used": 25
             }):
            
            result = await rag_engine.generate_context_aware_response(
                incoming_email=sample_email,
                user_id="test-user-123",
                writing_style=sample_writing_style,
                max_context_length=2000
            )
            
            assert "response_text" in result
            assert "confidence_score" in result
            assert "context_sources" in result
            assert "generation_metadata" in result
            assert len(result["response_text"]) > 0

    @pytest.mark.asyncio
    async def test_get_relevant_context(self, rag_engine, sample_email, mock_vector_manager):
        """Test context retrieval"""
        result = await rag_engine._get_relevant_context(
            incoming_email=sample_email,
            user_id="test-user-123", 
            max_context_length=1000
        )
        
        assert "context_text" in result
        assert "sources" in result
        assert "total_chunks" in result
        assert isinstance(result["sources"], list)
        mock_vector_manager.search_similar_emails.assert_called()

    @pytest.mark.asyncio
    async def test_generate_llm_response(self, rag_engine, sample_email, sample_writing_style):
        """Test LLM response generation"""
        with patch.object(rag_engine, 'initialize_qa_chains'), \
             patch('src.services.rag_engine.ChatOpenAI') as mock_chat:
            
            # Setup mock LLM
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(
                content="Thank you for your email regarding the project status. I will review the current progress and provide you with a detailed update."
            )
            mock_chat.return_value = mock_llm
            
            context = "Previous email: Thanks for the update."
            
            result = await rag_engine._generate_llm_response(
                incoming_email=sample_email,
                context=context,
                user_id="test-user-123",
                writing_style=sample_writing_style
            )
            
            assert "response_text" in result
            assert "model_used" in result
            assert len(result["response_text"]) > 0

    def test_build_context_prompt(self, rag_engine, sample_email, sample_writing_style):
        """Test context prompt building"""
        context_sources = [
            {"text": "Previous response about project status", "metadata": {"email_id": "1"}},
            {"text": "Client communication patterns", "metadata": {"type": "pattern"}}
        ]
        
        prompt = rag_engine._build_context_prompt(
            incoming_email=sample_email,
            context_sources=context_sources,
            writing_style=sample_writing_style
        )
        
        assert "Project Status Inquiry" in prompt  # Subject should be included
        assert "project status" in prompt.lower()  # Email content
        assert "formality" in prompt.lower()  # Writing style info
        assert len(prompt) > 100  # Should be substantial

    def test_format_context_sources(self, rag_engine):
        """Test context source formatting"""
        sources = [
            {
                "text": "Thank you for your email. I will review it.",
                "metadata": {"email_id": "email_1", "chunk_index": 0},
                "distance": 0.1
            },
            {
                "text": "I appreciate your patience with this matter.",
                "metadata": {"response_type": "acknowledgment"},
                "distance": 0.2
            }
        ]
        
        formatted = rag_engine._format_context_sources(sources, max_length=500)
        
        assert "Context 1:" in formatted
        assert "Context 2:" in formatted
        assert "Thank you for your email" in formatted
        assert len(formatted) <= 500

    @pytest.mark.asyncio
    async def test_filter_context_by_relevance(self, rag_engine, sample_email):
        """Test context filtering by relevance"""
        contexts = {
            "user_emails_test_user": [
                {"text": "project status update", "distance": 0.1},
                {"text": "unrelated content", "distance": 0.8}
            ],
            "user_responses_general": [
                {"text": "thank you for inquiry", "distance": 0.2},
                {"text": "completely different topic", "distance": 0.9}
            ]
        }
        
        filtered = await rag_engine._filter_context_by_relevance(
            contexts=contexts,
            incoming_email=sample_email,
            relevance_threshold=0.5
        )
        
        # Should keep only relevant contexts (distance < 0.5)
        assert len(filtered) == 2
        assert all(ctx["distance"] < 0.5 for ctx in filtered)

    def test_apply_writing_style(self, rag_engine, sample_writing_style):
        """Test writing style application"""
        response = "thanks for the email. i'll check and respond soon."
        
        styled_response = rag_engine._apply_writing_style(
            response=response,
            writing_style=sample_writing_style
        )
        
        # Should be more formal based on formality score
        assert "thank you" in styled_response.lower()
        assert "I will" in styled_response or "I'll" in styled_response

    def test_calculate_confidence_score(self, rag_engine):
        """Test confidence score calculation"""
        context_sources = [
            {"distance": 0.1, "metadata": {}},
            {"distance": 0.3, "metadata": {}},
            {"distance": 0.7, "metadata": {}}
        ]
        
        # High quality context should give high confidence
        confidence = rag_engine._calculate_confidence_score(
            context_sources=context_sources,
            response_length=50,
            style_applied=True
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be confident with good context

    def test_extract_keywords(self, rag_engine, sample_email):
        """Test keyword extraction"""
        keywords = rag_engine._extract_keywords(sample_email.body_text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert any("project" in keyword.lower() for keyword in keywords)
        assert any("status" in keyword.lower() for keyword in keywords)

    @pytest.mark.asyncio
    async def test_error_handling(self, rag_engine, sample_email):
        """Test error handling in response generation"""
        with patch.object(rag_engine, '_get_relevant_context', side_effect=Exception("Vector DB error")):
            
            result = await rag_engine.generate_context_aware_response(
                incoming_email=sample_email,
                user_id="test-user-123"
            )
            
            # Should still return a result (fallback)
            assert "response_text" in result
            assert "error" in result.get("generation_metadata", {})

    @pytest.mark.asyncio
    async def test_memory_management(self, rag_engine):
        """Test conversation memory management"""
        with patch('src.services.rag_engine.ConversationBufferMemory') as mock_memory:
            mock_memory_instance = Mock()
            mock_memory.return_value = mock_memory_instance
            
            await rag_engine.initialize_qa_chains("test-user-123")
            
            # Should store memory for user
            assert "test-user-123" in rag_engine.conversation_memories
            mock_memory.assert_called()

    def test_prompt_templates(self, rag_engine):
        """Test prompt template generation"""
        # Test different template scenarios
        email = EmailMessage(
            id="test",
            subject="Urgent: Payment Issue",
            body_text="We have an urgent payment issue that needs immediate attention.",
            sender="client@company.com"
        )
        
        style = WritingStyleProfile(
            user_id="test",
            formality_score=0.9,  # Very formal
            common_phrases=["I sincerely appreciate"]
        )
        
        prompt = rag_engine._build_context_prompt(
            incoming_email=email,
            context_sources=[],
            writing_style=style
        )
        
        assert "urgent" in prompt.lower()
        assert "formal" in prompt.lower()
        assert "payment" in prompt.lower()

    @pytest.mark.asyncio 
    async def test_context_length_limiting(self, rag_engine, sample_email, mock_vector_manager):
        """Test context length limiting"""
        # Mock large context response
        large_contexts = {
            "user_emails_test": [
                {"text": "Very long text " * 100, "distance": 0.1, "metadata": {}}
                for _ in range(10)
            ]
        }
        mock_vector_manager.search_similar_emails.return_value = large_contexts
        
        result = await rag_engine._get_relevant_context(
            incoming_email=sample_email,
            user_id="test-user-123",
            max_context_length=500  # Small limit
        )
        
        # Should respect length limit
        assert len(result["context_text"]) <= 600  # Some buffer for formatting
        assert result["total_chunks"] > 0

    def test_style_scoring(self, rag_engine):
        """Test writing style scoring"""
        formal_text = "I would be delighted to assist you with this matter."
        casual_text = "Sure, I can help with that!"
        
        formal_score = rag_engine._calculate_formality_score(formal_text)
        casual_score = rag_engine._calculate_formality_score(casual_text)
        
        assert formal_score > casual_score
        assert 0.0 <= formal_score <= 1.0
        assert 0.0 <= casual_score <= 1.0