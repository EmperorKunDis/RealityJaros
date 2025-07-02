import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from src.services.email_analyzer import EmailAnalysisEngine
from src.services.client_analyzer import ClientRelationshipAnalyzer  
from src.services.style_analyzer import WritingStyleAnalyzer
from src.services.topic_analyzer import TopicAnalyzer
from src.models.email import EmailMessage
from src.models.client import Client

@pytest.fixture
def mock_client_analyzer():
    """Mock client relationship analyzer"""
    mock = Mock(spec=ClientRelationshipAnalyzer)
    mock.analyze_client_relationship = AsyncMock(return_value={
        "client_email": "client@example.com",
        "relationship_strength": 0.8,
        "interaction_frequency": "weekly",
        "business_category": "technology",
        "communication_patterns": {
            "avg_response_time": "2 hours",
            "formality_level": 0.7,
            "topics": ["project updates", "meetings"]
        }
    })
    return mock

@pytest.fixture
def mock_style_analyzer():
    """Mock writing style analyzer"""
    mock = Mock(spec=WritingStyleAnalyzer)
    mock.analyze_writing_style = AsyncMock(return_value={
        "formality_score": 0.7,
        "tone": "professional",
        "common_phrases": ["Thank you for", "I appreciate"],
        "closing_patterns": ["Best regards", "Sincerely"],
        "avg_sentence_length": 15.5,
        "confidence_score": 0.8
    })
    return mock

@pytest.fixture
def mock_topic_analyzer():
    """Mock topic analyzer"""
    mock = Mock(spec=TopicAnalyzer)
    mock.analyze_email_topics = AsyncMock(return_value={
        "primary_topics": ["project management", "status update"],
        "sentiment": "neutral",
        "urgency_level": "medium",
        "business_category": "project_communication",
        "key_entities": ["Project Alpha", "Q4 deadline"],
        "confidence_score": 0.85
    })
    return mock

@pytest.fixture
def email_analyzer(mock_client_analyzer, mock_style_analyzer, mock_topic_analyzer):
    """Email analysis engine instance"""
    return EmailAnalysisEngine(
        client_analyzer=mock_client_analyzer,
        style_analyzer=mock_style_analyzer,
        topic_analyzer=mock_topic_analyzer
    )

@pytest.fixture
def sample_emails():
    """Sample emails for testing"""
    return [
        EmailMessage(
            id="email_1",
            sender="John Doe <john@techcorp.com>",
            subject="Project Alpha Status Update",
            body_text="Hi there, I wanted to check on the progress of Project Alpha. Could you please provide an update on the current status and any blockers?",
            received_at=datetime(2024, 1, 15, 10, 30),
            is_analyzed=False
        ),
        EmailMessage(
            id="email_2",
            sender="Sarah Wilson <sarah@designstudio.com>",
            subject="Meeting Request - UI Review",
            body_text="Hello! I would like to schedule a meeting to review the UI designs for our upcoming project. Are you available next week?",
            received_at=datetime(2024, 1, 16, 14, 20),
            is_analyzed=False
        ),
        EmailMessage(
            id="email_3", 
            sender="mike.chen@startup.io",
            subject="Urgent: Server Issues",
            body_text="We're experiencing critical server issues that need immediate attention. Please respond ASAP.",
            received_at=datetime(2024, 1, 17, 9, 45),
            is_analyzed=False
        )
    ]

@pytest.fixture
def sample_client():
    """Sample client for testing"""
    return Client(
        id="client_1",
        user_id="test_user_123",
        client_name="TechCorp Solutions",
        email_address="john@techcorp.com",
        business_category="technology",
        relationship_strength=0.8,
        interaction_frequency="weekly"
    )

class TestEmailAnalysisEngine:
    """Test cases for Email Analysis Engine"""

    @pytest.mark.asyncio
    async def test_analyze_single_email(self, email_analyzer, sample_emails):
        """Test analysis of a single email"""
        email = sample_emails[0]
        
        result = await email_analyzer.analyze_email(
            email=email,
            user_id="test_user_123"
        )
        
        assert "client_analysis" in result
        assert "style_analysis" in result
        assert "topic_analysis" in result
        assert "overall_analysis" in result
        
        # Check overall analysis structure
        overall = result["overall_analysis"]
        assert "priority_score" in overall
        assert "requires_immediate_attention" in overall
        assert "recommended_response_type" in overall
        assert "analysis_confidence" in overall

    @pytest.mark.asyncio
    async def test_analyze_email_batch(self, email_analyzer, sample_emails):
        """Test batch email analysis"""
        result = await email_analyzer.analyze_email_batch(
            emails=sample_emails,
            user_id="test_user_123"
        )
        
        assert "analyzed_emails" in result
        assert "batch_summary" in result
        assert len(result["analyzed_emails"]) == len(sample_emails)
        
        # Check batch summary
        summary = result["batch_summary"]
        assert "total_emails" in summary
        assert "high_priority_count" in summary
        assert "urgent_emails" in summary
        assert "avg_analysis_confidence" in summary

    @pytest.mark.asyncio
    async def test_comprehensive_analysis(self, email_analyzer, sample_emails):
        """Test comprehensive user analysis"""
        result = await email_analyzer.comprehensive_user_analysis(
            user_id="test_user_123",
            emails=sample_emails
        )
        
        assert "communication_patterns" in result
        assert "client_relationships" in result
        assert "writing_style_profile" in result
        assert "topic_preferences" in result
        assert "recommendations" in result
        
        # Check communication patterns
        patterns = result["communication_patterns"]
        assert "email_volume_trends" in patterns
        assert "response_time_patterns" in patterns
        assert "peak_communication_hours" in patterns

    def test_calculate_priority_score(self, email_analyzer):
        """Test priority score calculation"""
        # Test urgent email
        urgent_analysis = {
            "topic_analysis": {"urgency_level": "high", "sentiment": "negative"},
            "client_analysis": {"relationship_strength": 0.9}
        }
        
        priority = email_analyzer._calculate_priority_score(urgent_analysis)
        assert priority >= 0.7  # Should be high priority
        
        # Test normal email
        normal_analysis = {
            "topic_analysis": {"urgency_level": "low", "sentiment": "neutral"},
            "client_analysis": {"relationship_strength": 0.5}
        }
        
        priority = email_analyzer._calculate_priority_score(normal_analysis)
        assert priority <= 0.6  # Should be lower priority

    def test_determine_response_type(self, email_analyzer):
        """Test response type determination"""
        # Test meeting request
        meeting_analysis = {
            "topic_analysis": {"primary_topics": ["meeting", "schedule"]},
            "style_analysis": {"tone": "professional"}
        }
        
        response_type = email_analyzer._determine_response_type(meeting_analysis)
        assert response_type in ["meeting_response", "scheduling", "acknowledgment"]
        
        # Test urgent request
        urgent_analysis = {
            "topic_analysis": {"urgency_level": "high", "primary_topics": ["problem", "issue"]},
            "style_analysis": {"tone": "urgent"}
        }
        
        response_type = email_analyzer._determine_response_type(urgent_analysis)
        assert response_type in ["urgent_response", "immediate_action"]

    @pytest.mark.asyncio
    async def test_extract_communication_patterns(self, email_analyzer, sample_emails):
        """Test communication pattern extraction"""
        patterns = await email_analyzer._extract_communication_patterns(
            emails=sample_emails,
            user_id="test_user_123"
        )
        
        assert "email_volume_trends" in patterns
        assert "response_time_patterns" in patterns
        assert "peak_communication_hours" in patterns
        assert "sender_frequency" in patterns
        
        # Check email volume trends
        volume = patterns["email_volume_trends"]
        assert "daily_average" in volume
        assert "weekly_pattern" in volume
        
        # Check peak hours
        peak_hours = patterns["peak_communication_hours"]
        assert isinstance(peak_hours, list)
        assert all(0 <= hour <= 23 for hour in peak_hours)

    @pytest.mark.asyncio
    async def test_analyze_client_relationships(self, email_analyzer, sample_emails, mock_client_analyzer):
        """Test client relationship analysis"""
        relationships = await email_analyzer._analyze_client_relationships(
            emails=sample_emails,
            user_id="test_user_123"
        )
        
        assert "clients" in relationships
        assert "relationship_summary" in relationships
        
        # Should have analyzed each unique sender
        unique_senders = len(set(email.sender for email in sample_emails))
        assert len(relationships["clients"]) <= unique_senders
        
        # Check relationship summary
        summary = relationships["relationship_summary"]
        assert "total_clients" in summary
        assert "strong_relationships" in summary
        assert "avg_relationship_strength" in summary

    def test_extract_business_insights(self, email_analyzer):
        """Test business insights extraction"""
        analyzed_emails = [
            {
                "email_id": "email_1",
                "topic_analysis": {
                    "business_category": "project_management",
                    "urgency_level": "medium"
                },
                "client_analysis": {
                    "business_category": "technology"
                }
            },
            {
                "email_id": "email_2",
                "topic_analysis": {
                    "business_category": "design",
                    "urgency_level": "low"
                },
                "client_analysis": {
                    "business_category": "creative"
                }
            }
        ]
        
        insights = email_analyzer._extract_business_insights(analyzed_emails)
        
        assert "category_distribution" in insights
        assert "urgency_patterns" in insights
        assert "communication_trends" in insights

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, email_analyzer, sample_emails):
        """Test recommendation generation"""
        comprehensive_analysis = {
            "communication_patterns": {
                "response_time_patterns": {"avg_response_time": "4 hours"},
                "peak_communication_hours": [9, 10, 14, 15]
            },
            "writing_style_profile": {
                "formality_score": 0.7,
                "common_phrases": ["Thank you"]
            },
            "topic_preferences": {
                "primary_topics": ["projects", "meetings"]
            }
        }
        
        recommendations = await email_analyzer._generate_recommendations(
            analysis_data=comprehensive_analysis,
            user_id="test_user_123"
        )
        
        assert "response_templates" in recommendations
        assert "automation_suggestions" in recommendations
        assert "communication_improvements" in recommendations
        assert "priority_rules" in recommendations

    @pytest.mark.asyncio
    async def test_update_analysis_flags(self, email_analyzer, sample_emails):
        """Test analysis flag updates"""
        with patch('src.services.email_analyzer.AsyncSessionLocal') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            mock_session.return_value.commit = AsyncMock()
            
            await email_analyzer._update_analysis_flags(
                emails=sample_emails,
                user_id="test_user_123"
            )
            
            # Should mark all emails as analyzed
            for email in sample_emails:
                assert email.is_analyzed == True
                assert email.analyzed_at is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, email_analyzer, sample_emails, mock_style_analyzer):
        """Test error handling in analysis"""
        # Simulate analyzer error
        mock_style_analyzer.analyze_writing_style.side_effect = Exception("Analysis failed")
        
        result = await email_analyzer.analyze_email(
            email=sample_emails[0],
            user_id="test_user_123"
        )
        
        # Should still return a result with error information
        assert "error" in result.get("style_analysis", {})
        assert result["overall_analysis"]["analysis_confidence"] < 0.5

    def test_confidence_score_calculation(self, email_analyzer):
        """Test confidence score calculation"""
        analysis_results = {
            "client_analysis": {"confidence_score": 0.8},
            "style_analysis": {"confidence_score": 0.7},
            "topic_analysis": {"confidence_score": 0.9}
        }
        
        confidence = email_analyzer._calculate_analysis_confidence(analysis_results)
        
        # Should be average of individual confidences
        expected = (0.8 + 0.7 + 0.9) / 3
        assert abs(confidence - expected) < 0.01

    @pytest.mark.asyncio
    async def test_timeline_analysis(self, email_analyzer, sample_emails):
        """Test timeline-based analysis"""
        timeline = await email_analyzer._analyze_communication_timeline(
            emails=sample_emails,
            user_id="test_user_123"
        )
        
        assert "daily_patterns" in timeline
        assert "weekly_patterns" in timeline
        assert "monthly_trends" in timeline
        
        # Check daily patterns
        daily = timeline["daily_patterns"]
        assert all(day in daily for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])

    def test_sentiment_aggregation(self, email_analyzer):
        """Test sentiment aggregation"""
        email_analyses = [
            {"topic_analysis": {"sentiment": "positive"}},
            {"topic_analysis": {"sentiment": "neutral"}},
            {"topic_analysis": {"sentiment": "negative"}}
        ]
        
        sentiment_summary = email_analyzer._aggregate_sentiment(email_analyses)
        
        assert "overall_sentiment" in sentiment_summary
        assert "sentiment_distribution" in sentiment_summary
        assert sentiment_summary["sentiment_distribution"]["positive"] == 1
        assert sentiment_summary["sentiment_distribution"]["neutral"] == 1
        assert sentiment_summary["sentiment_distribution"]["negative"] == 1

    @pytest.mark.asyncio
    async def test_performance_metrics(self, email_analyzer, sample_emails):
        """Test performance metrics collection"""
        start_time = datetime.utcnow()
        
        result = await email_analyzer.analyze_email_batch(
            emails=sample_emails,
            user_id="test_user_123"
        )
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should complete in reasonable time
        assert processing_time < 30  # 30 seconds max for test data
        
        # Check if performance metrics are included
        if "performance_metrics" in result:
            metrics = result["performance_metrics"]
            assert "processing_time_ms" in metrics
            assert "emails_per_second" in metrics

    def test_text_preprocessing(self, email_analyzer):
        """Test text preprocessing for analysis"""
        raw_text = "Hi there!!! This is a TEST email with    extra spaces and\n\nnewlines."
        
        processed = email_analyzer._preprocess_text(raw_text)
        
        assert "!!!" not in processed  # Should normalize punctuation
        assert "  " not in processed   # Should normalize whitespace
        assert processed.count("\n") <= 1  # Should normalize newlines

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, email_analyzer, sample_emails):
        """Test concurrent analysis of multiple emails"""
        import asyncio
        
        # Analyze emails concurrently
        tasks = [
            email_analyzer.analyze_email(email, "test_user_123")
            for email in sample_emails
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        assert len(results) == len(sample_emails)
        assert all(not isinstance(result, Exception) for result in results)

    def test_priority_thresholds(self, email_analyzer):
        """Test priority threshold configuration"""
        # Test different urgency levels
        test_cases = [
            {"urgency_level": "critical", "expected_min": 0.9},
            {"urgency_level": "high", "expected_min": 0.7},
            {"urgency_level": "medium", "expected_min": 0.4},
            {"urgency_level": "low", "expected_min": 0.0}
        ]
        
        for case in test_cases:
            analysis = {
                "topic_analysis": {"urgency_level": case["urgency_level"]},
                "client_analysis": {"relationship_strength": 0.5}
            }
            
            priority = email_analyzer._calculate_priority_score(analysis)
            assert priority >= case["expected_min"]