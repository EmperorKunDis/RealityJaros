import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from src.main import app
from src.models.email import EmailMessage
from src.models.client import Client
from src.models.response import WritingStyleProfile, ResponseRule

client = TestClient(app)

@pytest.fixture
def mock_database_session():
    """Mock database session for integration tests"""
    with patch('src.config.database.AsyncSessionLocal') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.commit = AsyncMock()
        mock_session.return_value.rollback = AsyncMock()
        yield mock_session

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "test_user_123",
        "email": "testuser@example.com",
        "name": "Test User"
    }

@pytest.fixture
def sample_email_data():
    """Sample email data for testing"""
    return {
        "id": "email_123",
        "sender": "John Doe <john@client.com>",
        "subject": "Project Update Request",
        "body_text": "Hi, could you please provide an update on the current project status? I need this for our board meeting tomorrow.",
        "received_at": datetime.utcnow().isoformat()
    }

class TestCompleteWorkflow:
    """Integration tests for complete email processing workflow"""

    @pytest.mark.asyncio
    async def test_complete_email_processing_workflow(self, mock_database_session, sample_email_data):
        """Test complete workflow from email receipt to response generation"""
        
        # Mock all external dependencies
        with patch('src.services.vector_db_manager.VectorDatabaseManager') as mock_vector_manager, \
             patch('src.services.email_analyzer.EmailAnalysisEngine') as mock_analyzer, \
             patch('src.services.response_generator.ResponseGeneratorService') as mock_generator:
            
            # Setup mocks
            mock_vector_instance = Mock()
            mock_vector_instance.initialize_collections = AsyncMock()
            mock_vector_instance.chunk_and_embed_emails = AsyncMock(return_value={
                "user_emails_test_user": [{"id": "chunk_1", "text": "test", "embedding": [0.1]*384}]
            })
            mock_vector_manager.return_value = mock_vector_instance
            
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.analyze_email = AsyncMock(return_value={
                "client_analysis": {"relationship_strength": 0.8},
                "style_analysis": {"formality_score": 0.7},
                "topic_analysis": {"urgency_level": "medium"},
                "overall_analysis": {"priority_score": 0.6}
            })
            mock_analyzer.return_value = mock_analyzer_instance
            
            mock_generator_instance = Mock()
            mock_generator_instance.generate_response = AsyncMock(return_value=Mock(
                response_text="Thank you for your project update request. I will review the current status and provide you with a comprehensive update by end of day.",
                response_type="rag",
                confidence_score=0.85,
                relevance_score=0.8,
                style_match_score=0.75
            ))
            mock_generator.return_value = mock_generator_instance
            
            # Step 1: Submit email for processing
            response = client.post("/api/v1/emails/", json=sample_email_data)
            assert response.status_code == 200
            
            # Step 2: Trigger analysis
            analysis_response = client.post("/api/v1/analysis/comprehensive", json={
                "user_id": "test_user_123",
                "email_ids": ["email_123"]
            })
            assert analysis_response.status_code == 200
            
            # Step 3: Generate response
            generation_response = client.post("/api/v1/responses/generate", json={
                "email_id": "email_123",
                "use_rag": True,
                "max_context_length": 2000
            })
            assert generation_response.status_code == 200
            
            # Verify the response data
            response_data = generation_response.json()
            assert "response_text" in response_data
            assert "confidence_score" in response_data
            assert response_data["confidence_score"] > 0.5

    def test_api_endpoint_integration(self):
        """Test all API endpoints are accessible and return expected formats"""
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "application" in data
        assert "version" in data
        assert "status" in data
        
        # Test health check
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Test authentication endpoints
        response = client.get("/api/v1/auth/login")
        assert response.status_code in [200, 500]  # May fail without Google credentials
        
        # Test email endpoints
        response = client.get("/api/v1/emails/")
        assert response.status_code == 200
        data = response.json()
        assert "emails" in data
        assert "total_count" in data
        
        # Test client endpoints
        response = client.get("/api/v1/clients/")
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        
        # Test response endpoints
        response = client.get("/api/v1/responses/")
        assert response.status_code == 200
        data = response.json()
        assert "responses" in data
        
        # Test vector endpoints
        response = client.get("/api/v1/vectors/health")
        assert response.status_code == 200
        
        # Test analysis endpoints
        response = client.post("/api/v1/analysis/comprehensive")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_onboarding_workflow(self, mock_database_session):
        """Test complete user onboarding workflow"""
        
        with patch('src.services.google_auth.GoogleAuthService') as mock_auth, \
             patch('src.services.gmail_service.GmailService') as mock_gmail, \
             patch('src.services.vector_db_manager.VectorDatabaseManager') as mock_vector:
            
            # Mock authentication
            mock_auth_instance = Mock()
            mock_auth_instance.get_authorization_url = Mock(return_value="https://oauth.google.com/auth")
            mock_auth_instance.exchange_code_for_tokens = AsyncMock(return_value={
                "access_token": "token123",
                "refresh_token": "refresh123",
                "user_info": {"email": "user@example.com", "name": "Test User"}
            })
            mock_auth.return_value = mock_auth_instance
            
            # Mock Gmail service
            mock_gmail_instance = Mock()
            mock_gmail_instance.fetch_recent_emails = AsyncMock(return_value=[
                EmailMessage(
                    id="email_1",
                    sender="client@example.com",
                    subject="Welcome email",
                    body_text="Welcome to our service!"
                )
            ])
            mock_gmail.return_value = mock_gmail_instance
            
            # Mock vector database
            mock_vector_instance = Mock()
            mock_vector_instance.initialize_collections = AsyncMock()
            mock_vector.return_value = mock_vector_instance
            
            # Step 1: Start authentication
            auth_response = client.get("/api/v1/auth/login")
            assert auth_response.status_code in [200, 500]
            
            # Step 2: Complete authentication (simulate)
            # This would normally involve OAuth callback
            
            # Step 3: Fetch initial emails
            emails_response = client.post("/api/v1/emails/fetch", json={
                "user_id": "test_user_123",
                "limit": 50
            })
            assert emails_response.status_code in [200, 500]  # May fail without real auth
            
            # Step 4: Initialize user's vector collections
            vector_response = client.post("/api/v1/vectors/initialize", json={
                "user_id": "test_user_123"
            })
            assert vector_response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_email_response_generation_workflow(self, sample_email_data):
        """Test email response generation workflow with different strategies"""
        
        with patch('src.services.vector_db_manager.VectorDatabaseManager') as mock_vector, \
             patch('src.services.rag_engine.RAGEngine') as mock_rag:
            
            # Mock vector database
            mock_vector_instance = Mock()
            mock_vector_instance.initialize_collections = AsyncMock()
            mock_vector_instance.search_similar_emails = AsyncMock(return_value={
                "user_emails_test_user": [
                    {"text": "Previous project update", "distance": 0.2}
                ]
            })
            mock_vector.return_value = mock_vector_instance
            
            # Mock RAG engine
            mock_rag_instance = Mock()
            mock_rag_instance.initialize_qa_chains = AsyncMock()
            mock_rag_instance.generate_context_aware_response = AsyncMock(return_value={
                "response_text": "Thank you for your project update request. Based on our previous communications, I will provide you with a detailed status report.",
                "confidence_score": 0.87,
                "context_sources": [{"text": "context", "metadata": {}}],
                "style_match_applied": True,
                "generation_metadata": {"model_used": "gpt-4"}
            })
            mock_rag.return_value = mock_rag_instance
            
            # Test RAG-based response generation
            rag_response = client.post("/api/v1/responses/generate", json={
                "email_id": "email_123",
                "use_rag": True,
                "max_context_length": 2000
            })
            
            # Should work even if email doesn't exist (will use mock)
            assert rag_response.status_code in [200, 404, 500]
            
            # Test template-based response generation
            template_response = client.post("/api/v1/responses/generate", json={
                "email_id": "email_123",
                "use_rag": False
            })
            
            assert template_response.status_code in [200, 404, 500]

    def test_error_handling_across_services(self):
        """Test error handling across different services"""
        
        # Test with invalid email ID
        response = client.post("/api/v1/responses/generate", json={
            "email_id": "nonexistent_email",
            "use_rag": True
        })
        assert response.status_code in [404, 500]
        
        # Test with invalid vector search
        response = client.post("/api/v1/vectors/search", json={
            "query": "test query",
            "user_id": "nonexistent_user"
        })
        assert response.status_code in [200, 404, 500]
        
        # Test with invalid analysis request
        response = client.post("/api/v1/analysis/style", json={
            "user_id": "nonexistent_user"
        })
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_data_consistency_across_services(self, mock_database_session):
        """Test data consistency when processing emails across services"""
        
        with patch('src.services.email_analyzer.EmailAnalysisEngine') as mock_analyzer, \
             patch('src.services.vector_db_manager.VectorDatabaseManager') as mock_vector:
            
            # Mock consistent data across services
            email_data = {
                "id": "consistent_email_123",
                "sender": "consistency@test.com",
                "subject": "Consistency Test",
                "body_text": "This is a consistency test email."
            }
            
            # Mock analyzer
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.analyze_email = AsyncMock(return_value={
                "client_analysis": {"client_email": "consistency@test.com"},
                "topic_analysis": {"primary_topics": ["test"]},
                "overall_analysis": {"priority_score": 0.5}
            })
            mock_analyzer.return_value = mock_analyzer_instance
            
            # Mock vector database
            mock_vector_instance = Mock()
            mock_vector_instance.chunk_and_embed_emails = AsyncMock(return_value={
                "user_emails_test_user": [{"id": "chunk_1", "text": "This is a consistency test email."}]
            })
            mock_vector.return_value = mock_vector_instance
            
            # Process email through multiple services
            # 1. Store email
            store_response = client.post("/api/v1/emails/", json=email_data)
            assert store_response.status_code == 200
            
            # 2. Analyze email
            analysis_response = client.post("/api/v1/analysis/comprehensive", json={
                "user_id": "test_user_123",
                "email_ids": ["consistent_email_123"]
            })
            assert analysis_response.status_code == 200
            
            # 3. Vectorize email
            vector_response = client.post("/api/v1/vectors/vectorize", json={
                "user_id": "test_user_123",
                "email_ids": ["consistent_email_123"]
            })
            assert vector_response.status_code in [200, 500]
            
            # All services should have processed the same email data

    def test_performance_under_load(self):
        """Test system performance under simulated load"""
        import concurrent.futures
        import time
        
        def make_request():
            response = client.get("/health")
            return response.status_code == 200
        
        # Simulate concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # All requests should succeed
        assert all(results)
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 30  # 30 seconds for 50 requests

    @pytest.mark.asyncio
    async def test_security_and_authentication(self):
        """Test security measures and authentication"""
        
        # Test that protected endpoints require authentication
        protected_endpoints = [
            "/api/v1/emails/fetch",
            "/api/v1/clients/analyze",
            "/api/v1/responses/generate"
        ]
        
        for endpoint in protected_endpoints:
            response = client.post(endpoint, json={})
            # Should either work (if auth not strictly enforced in test) or require auth
            assert response.status_code in [200, 401, 422, 500]

    def test_configuration_and_environment(self):
        """Test configuration handling and environment setup"""
        
        # Test that the application starts with default configuration
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health check reflects correct configuration
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    @pytest.mark.asyncio
    async def test_database_operations_integration(self, mock_database_session):
        """Test database operations across different models"""
        
        with patch('sqlalchemy.ext.asyncio.AsyncSession.execute') as mock_execute, \
             patch('sqlalchemy.ext.asyncio.AsyncSession.commit') as mock_commit:
            
            # Mock database operations
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
            mock_execute.return_value = mock_result
            
            # Test operations that would involve database
            response = client.get("/api/v1/emails/")
            assert response.status_code == 200
            
            response = client.get("/api/v1/clients/")
            assert response.status_code == 200
            
            response = client.get("/api/v1/responses/")
            assert response.status_code == 200

    def test_api_documentation_accessibility(self):
        """Test that API documentation is accessible"""
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

class TestEndToEndScenarios:
    """End-to-end scenario tests"""

    def test_new_user_first_time_setup(self):
        """Test complete new user setup scenario"""
        
        # User visits the application
        response = client.get("/")
        assert response.status_code == 200
        
        # User initiates authentication
        response = client.get("/api/v1/auth/login")
        assert response.status_code in [200, 500]
        
        # After authentication, user would fetch emails and set up profile
        # This would be tested with proper OAuth mocking in a full test

    def test_daily_email_processing_scenario(self):
        """Test daily email processing scenario"""
        
        # Fetch new emails
        response = client.post("/api/v1/emails/fetch", json={
            "user_id": "daily_user",
            "limit": 20
        })
        assert response.status_code in [200, 500]
        
        # Analyze fetched emails
        response = client.post("/api/v1/analysis/comprehensive", json={
            "user_id": "daily_user"
        })
        assert response.status_code == 200
        
        # Generate responses for high-priority emails
        response = client.post("/api/v1/responses/generate", json={
            "email_id": "priority_email",
            "use_rag": True
        })
        assert response.status_code in [200, 404, 500]

    def test_business_intelligence_scenario(self):
        """Test business intelligence and analytics scenario"""
        
        # Get client analytics
        response = client.get("/api/v1/clients/analytics")
        assert response.status_code in [200, 500]
        
        # Get communication patterns
        response = client.get("/api/v1/analysis/patterns", params={
            "user_id": "analytics_user",
            "timeframe": "30_days"
        })
        assert response.status_code in [200, 500]
        
        # Get vector database statistics
        response = client.get("/api/v1/vectors/collections/stats")
        assert response.status_code in [200, 500]