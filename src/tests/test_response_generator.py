import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from src.services.response_generator import ResponseGeneratorService, ResponseGenerationResult
from src.services.rag_engine import RAGEngine
from src.services.rule_generator import RuleGeneratorService
from src.services.style_analyzer import WritingStyleAnalyzer
from src.models.email import EmailMessage
from src.models.response import WritingStyleProfile, ResponseRule

@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine"""
    mock = Mock(spec=RAGEngine)
    mock.generate_context_aware_response = AsyncMock(return_value={
        "response_text": "Thank you for your email. I will review it and get back to you soon.",
        "confidence_score": 0.85,
        "context_sources": [
            {"text": "Previous email context", "score": 0.9}
        ],
        "style_match_applied": True,
        "generation_metadata": {"model_used": "gpt-4"}
    })
    return mock

@pytest.fixture
def mock_rule_generator():
    """Mock rule generator"""
    mock = Mock(spec=RuleGeneratorService)
    return mock

@pytest.fixture
def mock_style_analyzer():
    """Mock style analyzer"""
    mock = Mock(spec=WritingStyleAnalyzer)
    return mock

@pytest.fixture
def response_generator(mock_rag_engine, mock_rule_generator, mock_style_analyzer):
    """Response generator service instance"""
    return ResponseGeneratorService(
        rag_engine=mock_rag_engine,
        rule_generator=mock_rule_generator,
        style_analyzer=mock_style_analyzer
    )

@pytest.fixture
def sample_email():
    """Sample email for testing"""
    return EmailMessage(
        id="test-email-123",
        sender="john.doe@example.com",
        subject="Project Update Request",
        body_text="Hi, could you please provide an update on the current project status?",
        received_at=datetime.utcnow()
    )

@pytest.fixture
def sample_user_profile():
    """Sample user writing style profile"""
    return WritingStyleProfile(
        user_id="test-user-123",
        formality_score=0.7,
        common_phrases=["Thank you for reaching out", "I appreciate your patience"],
        closing_patterns=["Best regards", "Kind regards"],
        confidence_score=0.8
    )

@pytest.fixture
def sample_rule():
    """Sample response rule"""
    return ResponseRule(
        id="test-rule-123",
        user_id="test-user-123",
        rule_name="Meeting Request Auto Response",
        rule_category="auto_reply",
        trigger_keywords=["meeting", "schedule", "call"],
        response_template="Thank you for your meeting request. I will check my calendar and get back to you with available times.",
        success_rate=0.9,
        is_active=True,
        priority=1
    )

class TestResponseGeneratorService:
    """Test cases for Response Generator Service"""

    @pytest.mark.asyncio
    async def test_generate_rag_response(self, response_generator, sample_email, sample_user_profile, mock_rag_engine):
        """Test RAG-only response generation"""
        with patch('src.services.response_generator.AsyncSessionLocal') as mock_session:
            # Mock database session
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            
            # Mock database queries
            with patch.object(response_generator, '_get_user_profile', return_value=sample_user_profile), \
                 patch.object(response_generator, '_get_client_info', return_value=None), \
                 patch.object(response_generator, '_get_applicable_rules', return_value=[]), \
                 patch.object(response_generator, '_store_generated_response'):
                
                result = await response_generator.generate_response(
                    incoming_email=sample_email,
                    user_id="test-user-123"
                )
                
                assert isinstance(result, ResponseGenerationResult)
                assert result.response_type == "rag"
                assert result.confidence_score >= 0.5
                assert len(result.response_text) > 0
                assert mock_rag_engine.generate_context_aware_response.called

    @pytest.mark.asyncio
    async def test_generate_rule_based_response(self, response_generator, sample_email, sample_user_profile, sample_rule):
        """Test rule-based response generation"""
        with patch('src.services.response_generator.AsyncSessionLocal') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch.object(response_generator, '_get_user_profile', return_value=sample_user_profile), \
                 patch.object(response_generator, '_get_client_info', return_value=None), \
                 patch.object(response_generator, '_get_applicable_rules', return_value=[sample_rule]), \
                 patch.object(response_generator, '_store_generated_response'):
                
                result = await response_generator.generate_response(
                    incoming_email=sample_email,
                    user_id="test-user-123"
                )
                
                assert isinstance(result, ResponseGenerationResult)
                assert result.response_type == "template"
                assert result.rule_applied == sample_rule.rule_name
                assert len(result.response_text) > 0

    @pytest.mark.asyncio
    async def test_generate_hybrid_response(self, response_generator, sample_email, sample_user_profile, sample_rule, mock_rag_engine):
        """Test hybrid response generation"""
        # Modify rule to have lower success rate to trigger hybrid mode
        sample_rule.success_rate = 0.6
        
        with patch('src.services.response_generator.AsyncSessionLocal') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch.object(response_generator, '_get_user_profile', return_value=sample_user_profile), \
                 patch.object(response_generator, '_get_client_info', return_value=None), \
                 patch.object(response_generator, '_get_applicable_rules', return_value=[sample_rule]), \
                 patch.object(response_generator, '_store_generated_response'):
                
                result = await response_generator.generate_response(
                    incoming_email=sample_email,
                    user_id="test-user-123"
                )
                
                assert isinstance(result, ResponseGenerationResult)
                assert result.response_type == "hybrid"
                assert mock_rag_engine.generate_context_aware_response.called

    @pytest.mark.asyncio
    async def test_generate_template_response(self, response_generator, sample_email):
        """Test template fallback response generation"""
        with patch('src.services.response_generator.AsyncSessionLocal') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch.object(response_generator, '_get_user_profile', return_value=None), \
                 patch.object(response_generator, '_get_client_info', return_value=None), \
                 patch.object(response_generator, '_get_applicable_rules', return_value=[]), \
                 patch.object(response_generator, '_store_generated_response'):
                
                result = await response_generator.generate_response(
                    incoming_email=sample_email,
                    user_id="test-user-123"
                )
                
                assert isinstance(result, ResponseGenerationResult)
                assert result.response_type == "template"
                assert len(result.response_text) > 0

    def test_rule_matches_email(self, response_generator, sample_email, sample_rule):
        """Test rule matching logic"""
        # Test with matching email
        matching_email = EmailMessage(
            id="test-email-123",
            sender="john@example.com",
            subject="Schedule a meeting",
            body_text="I would like to schedule a meeting with you"
        )
        
        result = asyncio.run(response_generator._rule_matches_email(sample_rule, matching_email))
        assert result == True
        
        # Test with non-matching email
        non_matching_email = EmailMessage(
            id="test-email-456",
            sender="jane@example.com", 
            subject="Invoice question",
            body_text="I have a question about my invoice"
        )
        
        result = asyncio.run(response_generator._rule_matches_email(sample_rule, non_matching_email))
        assert result == False

    def test_determine_generation_strategy(self, response_generator, sample_email):
        """Test strategy determination logic"""
        # High confidence rule should trigger rule-based
        high_conf_rule = ResponseRule(
            rule_name="High Confidence Rule",
            success_rate=0.95
        )
        
        strategy = response_generator._determine_generation_strategy(
            email=sample_email,
            user_profile=None,
            client_info=None,
            applicable_rules=[high_conf_rule],
            options=None
        )
        assert strategy == "rule_based"
        
        # High confidence profile should trigger RAG
        high_conf_profile = WritingStyleProfile(
            user_id="test-user",
            confidence_score=0.8
        )
        
        strategy = response_generator._determine_generation_strategy(
            email=sample_email,
            user_profile=high_conf_profile,
            client_info=None,
            applicable_rules=[],
            options=None
        )
        assert strategy == "rag_only"
        
        # No rules or profile should trigger template fallback
        strategy = response_generator._determine_generation_strategy(
            email=sample_email,
            user_profile=None,
            client_info=None,
            applicable_rules=[],
            options=None
        )
        assert strategy == "template_fallback"

    def test_style_matching(self, response_generator, sample_user_profile):
        """Test writing style application"""
        result = ResponseGenerationResult(
            response_text="thanks for your message. i'll get back to you soon.",
            response_type="test",
            confidence_score=0.7,
            relevance_score=0.8,
            style_match_score=0.5,
            generation_time_ms=100,
            model_used="test",
            tokens_used=10,
            context_sources=[]
        )
        
        updated_result = asyncio.run(
            response_generator._apply_style_matching(result, sample_user_profile)
        )
        
        # Should make text more formal
        assert "thank you" in updated_result.response_text.lower()
        assert updated_result.style_match_score > result.style_match_score

    def test_response_quality_validation(self, response_generator, sample_email):
        """Test response quality validation"""
        result = ResponseGenerationResult(
            response_text="Thank you for your email regarding the project update. I will review the current status and provide you with a comprehensive update shortly. Best regards.",
            response_type="test",
            confidence_score=0.7,
            relevance_score=0.8,
            style_match_score=0.6,
            generation_time_ms=100,
            model_used="test",
            tokens_used=25,
            context_sources=[]
        )
        
        validated_result = asyncio.run(
            response_generator._validate_response_quality(result, sample_email)
        )
        
        assert validated_result.quality_metrics is not None
        assert "word_count" in validated_result.quality_metrics
        assert "professional_tone" in validated_result.quality_metrics
        assert "has_greeting" in validated_result.quality_metrics
        assert "has_closing" in validated_result.quality_metrics

    def test_template_selection(self, response_generator):
        """Test template selection logic"""
        templates = response_generator._get_response_templates()
        
        # Test meeting request detection
        meeting_email = "I would like to schedule a meeting with you next week"
        template = response_generator._select_template(meeting_email, templates)
        assert "meeting" in template.lower()
        
        # Test information request detection
        info_email = "Could you please provide more information about the project?"
        template = response_generator._select_template(info_email, templates)
        assert "information" in template.lower()
        
        # Test generic fallback
        generic_email = "Hello there"
        template = response_generator._select_template(generic_email, templates)
        assert "Thank you for your email" in template

    @pytest.mark.asyncio
    async def test_error_handling(self, response_generator, sample_email):
        """Test error handling and fallback responses"""
        with patch('src.services.response_generator.AsyncSessionLocal') as mock_session:
            # Simulate database error
            mock_session.side_effect = Exception("Database connection failed")
            
            result = await response_generator.generate_response(
                incoming_email=sample_email,
                user_id="test-user-123"
            )
            
            # Should return fallback response
            assert result.response_type == "fallback"
            assert result.confidence_score < 0.5
            assert len(result.response_text) > 0

    def test_email_address_extraction(self, response_generator):
        """Test email address extraction utility"""
        # Test standard format
        email_str = "John Doe <john.doe@example.com>"
        result = response_generator._extract_email_address(email_str)
        assert result == "john.doe@example.com"
        
        # Test plain email
        email_str = "jane@example.com"
        result = response_generator._extract_email_address(email_str)
        assert result == "jane@example.com"
        
        # Test invalid input
        result = response_generator._extract_email_address("Not an email")
        assert result is None

    def test_sender_name_extraction(self, response_generator):
        """Test sender name extraction utility"""
        # Test standard format
        sender_str = "John Doe <john.doe@example.com>"
        result = response_generator._extract_sender_name(sender_str)
        assert result == "John Doe"
        
        # Test email only
        sender_str = "jane.smith@example.com"
        result = response_generator._extract_sender_name(sender_str)
        assert result == "Jane Smith"
        
        # Test empty input
        result = response_generator._extract_sender_name("")
        assert result == "there"