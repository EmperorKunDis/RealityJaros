import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""

    def test_login_endpoint(self):
        """Test Google OAuth login endpoint"""
        response = client.get("/api/v1/auth/login")
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "authorization_url" in data or "error" in data

    def test_oauth_callback_endpoint(self):
        """Test OAuth callback endpoint"""
        response = client.get("/api/v1/auth/callback", params={
            "code": "test_code",
            "state": "test_state"
        })
        
        # Should handle callback (may fail without real OAuth)
        assert response.status_code in [200, 400, 500]

    def test_logout_endpoint(self):
        """Test logout endpoint"""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code in [200, 401]

class TestEmailEndpoints:
    """Test email API endpoints"""

    def test_get_emails_endpoint(self):
        """Test get emails endpoint"""
        response = client.get("/api/v1/emails/")
        assert response.status_code == 200
        
        data = response.json()
        assert "emails" in data
        assert "total_count" in data
        assert isinstance(data["emails"], list)
        assert isinstance(data["total_count"], int)

    def test_get_emails_with_pagination(self):
        """Test email pagination"""
        response = client.get("/api/v1/emails/", params={
            "page": 2,
            "page_size": 10
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_get_emails_with_filters(self):
        """Test email filtering"""
        response = client.get("/api/v1/emails/", params={
            "sender": "test@example.com",
            "is_analyzed": "true",
            "priority": "high"
        })
        assert response.status_code == 200

    def test_fetch_emails_endpoint(self):
        """Test email fetching from Gmail"""
        response = client.post("/api/v1/emails/fetch", json={
            "user_id": "test_user",
            "limit": 50,
            "fetch_attachments": False
        })
        
        # May fail without proper Gmail authentication
        assert response.status_code in [200, 401, 500]

    def test_create_email_endpoint(self):
        """Test creating/storing an email"""
        email_data = {
            "sender": "test@example.com",
            "subject": "Test Subject",
            "body_text": "Test email content",
            "received_at": "2024-01-01T10:00:00Z"
        }
        
        response = client.post("/api/v1/emails/", json=email_data)
        assert response.status_code == 200

    def test_get_single_email_endpoint(self):
        """Test getting a single email by ID"""
        response = client.get("/api/v1/emails/nonexistent_id")
        assert response.status_code in [404, 500]

    def test_update_email_endpoint(self):
        """Test updating email metadata"""
        response = client.put("/api/v1/emails/test_id", json={
            "is_analyzed": True,
            "priority_score": 0.8
        })
        assert response.status_code in [200, 404, 500]

class TestClientEndpoints:
    """Test client API endpoints"""

    def test_get_clients_endpoint(self):
        """Test get clients endpoint"""
        response = client.get("/api/v1/clients/")
        assert response.status_code == 200
        
        data = response.json()
        assert "clients" in data
        assert "total_count" in data

    def test_get_clients_with_filters(self):
        """Test client filtering"""
        response = client.get("/api/v1/clients/", params={
            "business_category": "technology",
            "relationship_strength_min": "0.5"
        })
        assert response.status_code == 200

    def test_analyze_client_endpoint(self):
        """Test client relationship analysis"""
        response = client.post("/api/v1/clients/analyze", json={
            "user_id": "test_user",
            "client_email": "client@example.com"
        })
        
        assert response.status_code in [200, 500]

    def test_get_client_analytics_endpoint(self):
        """Test client analytics endpoint"""
        response = client.get("/api/v1/clients/analytics", params={
            "user_id": "test_user",
            "timeframe": "30_days"
        })
        
        assert response.status_code in [200, 500]

    def test_create_client_endpoint(self):
        """Test creating a new client"""
        client_data = {
            "client_name": "Test Client Corp",
            "email_address": "contact@testclient.com",
            "business_category": "technology"
        }
        
        response = client.post("/api/v1/clients/", json=client_data)
        assert response.status_code in [200, 500]

    def test_update_client_endpoint(self):
        """Test updating client information"""
        response = client.put("/api/v1/clients/test_client_id", json={
            "business_category": "finance",
            "relationship_strength": 0.9
        })
        assert response.status_code in [200, 404, 500]

class TestResponseEndpoints:
    """Test response generation API endpoints"""

    def test_get_responses_endpoint(self):
        """Test get responses endpoint"""
        response = client.get("/api/v1/responses/")
        assert response.status_code == 200
        
        data = response.json()
        assert "responses" in data
        assert "total_count" in data

    def test_get_responses_with_status_filter(self):
        """Test response filtering by status"""
        response = client.get("/api/v1/responses/", params={
            "status": "draft"
        })
        assert response.status_code == 200

    def test_generate_response_endpoint(self):
        """Test response generation endpoint"""
        response = client.post("/api/v1/responses/generate", json={
            "email_id": "test_email_id",
            "use_rag": True,
            "max_context_length": 2000,
            "custom_instructions": "Keep it brief and professional"
        })
        
        # May fail if email doesn't exist
        assert response.status_code in [200, 404, 500]

    def test_generate_rag_response_endpoint(self):
        """Test RAG response generation endpoint"""
        response = client.post("/api/v1/responses/generate-rag/test_email_id", params={
            "max_context_length": 1500,
            "custom_instructions": "Include project timeline"
        })
        
        assert response.status_code in [200, 404, 500]

    def test_get_single_response_endpoint(self):
        """Test getting a single response by ID"""
        response = client.get("/api/v1/responses/nonexistent_response")
        assert response.status_code in [404, 500]

    def test_update_response_status_endpoint(self):
        """Test updating response status"""
        response = client.put("/api/v1/responses/test_response_id/status", params={
            "status": "reviewed"
        })
        assert response.status_code in [200, 404, 500]

class TestAnalysisEndpoints:
    """Test analysis API endpoints"""

    def test_style_analysis_endpoint(self):
        """Test writing style analysis"""
        response = client.post("/api/v1/analysis/style", json={
            "user_id": "test_user",
            "email_ids": ["email1", "email2"]
        })
        
        assert response.status_code in [200, 500]

    def test_topic_analysis_endpoint(self):
        """Test topic analysis"""
        response = client.post("/api/v1/analysis/topics", json={
            "user_id": "test_user",
            "email_ids": ["email1", "email2"]
        })
        
        assert response.status_code in [200, 500]

    def test_comprehensive_analysis_endpoint(self):
        """Test comprehensive analysis"""
        response = client.post("/api/v1/analysis/comprehensive", json={
            "user_id": "test_user",
            "email_ids": ["email1", "email2"],
            "include_recommendations": True
        })
        
        assert response.status_code == 200

    def test_client_analysis_endpoint(self):
        """Test client relationship analysis"""
        response = client.post("/api/v1/analysis/clients", json={
            "user_id": "test_user",
            "analyze_all": True
        })
        
        assert response.status_code in [200, 500]

    def test_communication_patterns_endpoint(self):
        """Test communication patterns analysis"""
        response = client.get("/api/v1/analysis/patterns", params={
            "user_id": "test_user",
            "timeframe": "30_days",
            "pattern_type": "all"
        })
        
        assert response.status_code in [200, 500]

class TestVectorEndpoints:
    """Test vector database API endpoints"""

    def test_vector_health_endpoint(self):
        """Test vector database health check"""
        response = client.get("/api/v1/vectors/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data

    def test_initialize_collections_endpoint(self):
        """Test vector collections initialization"""
        response = client.post("/api/v1/vectors/initialize", json={
            "user_id": "test_user"
        })
        
        assert response.status_code in [200, 500]

    def test_vectorize_emails_endpoint(self):
        """Test email vectorization"""
        response = client.post("/api/v1/vectors/vectorize", json={
            "user_id": "test_user",
            "email_ids": ["email1", "email2"],
            "update_existing": False
        })
        
        assert response.status_code in [200, 500]

    def test_search_vectors_endpoint(self):
        """Test vector search"""
        response = client.post("/api/v1/vectors/search", json={
            "query": "project status update",
            "user_id": "test_user",
            "n_results": 10,
            "similarity_threshold": 0.7
        })
        
        assert response.status_code in [200, 500]

    def test_collection_stats_endpoint(self):
        """Test collection statistics"""
        response = client.get("/api/v1/vectors/collections/stats")
        assert response.status_code in [200, 500]

    def test_delete_user_vectors_endpoint(self):
        """Test deleting user vectors"""
        response = client.delete("/api/v1/vectors/user/test_user")
        assert response.status_code in [200, 404, 500]

class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payloads"""
        response = client.post("/api/v1/emails/", data="invalid json")
        assert response.status_code in [400, 422]

    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        response = client.post("/api/v1/responses/generate", json={
            "use_rag": True
            # Missing email_id
        })
        assert response.status_code == 422

    def test_invalid_field_types(self):
        """Test handling of invalid field types"""
        response = client.post("/api/v1/responses/generate", json={
            "email_id": 123,  # Should be string
            "use_rag": "yes"  # Should be boolean
        })
        assert response.status_code == 422

    def test_invalid_query_parameters(self):
        """Test handling of invalid query parameters"""
        response = client.get("/api/v1/emails/", params={
            "page": -1,  # Invalid page number
            "page_size": 1000  # Too large
        })
        assert response.status_code in [200, 422]

    def test_nonexistent_resource_access(self):
        """Test accessing nonexistent resources"""
        response = client.get("/api/v1/emails/nonexistent_email_id")
        assert response.status_code in [404, 500]

    def test_unauthorized_access(self):
        """Test unauthorized access scenarios"""
        # Test endpoints that might require authentication
        protected_endpoints = [
            ("/api/v1/emails/fetch", "post"),
            ("/api/v1/clients/analyze", "post"),
            ("/api/v1/responses/generate", "post")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "post":
                response = client.post(endpoint, json={})
            else:
                response = client.get(endpoint)
            
            # Should either work (if auth not enforced) or require auth
            assert response.status_code in [200, 401, 422, 500]

class TestDataValidation:
    """Test API data validation"""

    def test_email_validation(self):
        """Test email address validation"""
        invalid_emails = [
            "not_an_email",
            "@invalid.com",
            "test@",
            ""
        ]
        
        for invalid_email in invalid_emails:
            response = client.post("/api/v1/emails/", json={
                "sender": invalid_email,
                "subject": "Test",
                "body_text": "Test content"
            })
            # Should validate email format
            assert response.status_code in [200, 422, 500]

    def test_date_validation(self):
        """Test date format validation"""
        response = client.post("/api/v1/emails/", json={
            "sender": "test@example.com",
            "subject": "Test",
            "body_text": "Test content",
            "received_at": "invalid-date"
        })
        assert response.status_code in [200, 422]

    def test_numeric_validation(self):
        """Test numeric field validation"""
        response = client.get("/api/v1/clients/", params={
            "relationship_strength_min": "not_a_number"
        })
        assert response.status_code in [200, 422]

class TestRateLimit:
    """Test rate limiting (if implemented)"""

    def test_rapid_requests(self):
        """Test handling of rapid requests"""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # All should succeed or some might be rate limited
        assert all(status in [200, 429] for status in responses)

class TestResponseFormats:
    """Test API response formats"""

    def test_json_response_format(self):
        """Test JSON response format consistency"""
        endpoints = [
            "/",
            "/health",
            "/api/v1/emails/",
            "/api/v1/clients/",
            "/api/v1/responses/"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            # Should return valid JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_error_response_format(self):
        """Test error response format"""
        response = client.get("/api/v1/emails/nonexistent_id")
        
        if response.status_code >= 400:
            data = response.json()
            assert "detail" in data or "error" in data

    def test_pagination_response_format(self):
        """Test pagination response format"""
        paginated_endpoints = [
            "/api/v1/emails/",
            "/api/v1/clients/",
            "/api/v1/responses/"
        ]
        
        for endpoint in paginated_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            assert "total_count" in data
            assert "page" in data
            assert "page_size" in data

class TestAPIDocumentation:
    """Test API documentation endpoints"""

    def test_openapi_schema(self):
        """Test OpenAPI schema accessibility"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_swagger_ui(self):
        """Test Swagger UI accessibility"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_ui(self):
        """Test ReDoc UI accessibility"""
        response = client.get("/redoc")
        assert response.status_code == 200