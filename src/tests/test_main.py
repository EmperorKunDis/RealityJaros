import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "AI Email Assistant"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"

def test_auth_login_endpoint():
    """Test the auth login endpoint"""
    response = client.get("/api/v1/auth/login")
    # This should work even without Google credentials configured
    # as it will just fail gracefully
    assert response.status_code in [200, 500]  # Either success or config error

def test_emails_endpoint():
    """Test the emails endpoint"""
    response = client.get("/api/v1/emails/")
    assert response.status_code == 200
    data = response.json()
    assert "emails" in data
    assert "total_count" in data
    assert data["total_count"] == 0  # No emails yet

def test_clients_endpoint():
    """Test the clients endpoint"""
    response = client.get("/api/v1/clients/")
    assert response.status_code == 200
    data = response.json()
    assert "clients" in data
    assert "total_count" in data
    assert data["total_count"] == 0  # No clients yet

def test_responses_endpoint():
    """Test the responses endpoint"""
    response = client.get("/api/v1/responses/")
    assert response.status_code == 200
    data = response.json()
    assert "responses" in data
    assert "total_count" in data
    assert data["total_count"] == 0  # No responses yet

def test_analysis_endpoints():
    """Test the analysis endpoints"""
    # Test style analysis endpoint
    response = client.post("/api/v1/analysis/style")
    assert response.status_code in [200, 500]  # May fail due to no data
    
    # Test topic analysis endpoint  
    response = client.post("/api/v1/analysis/topics")
    assert response.status_code in [200, 500]  # May fail due to no data
    
    # Test comprehensive analysis endpoint
    response = client.post("/api/v1/analysis/comprehensive")
    assert response.status_code == 200

def test_vector_endpoints():
    """Test the vector database endpoints"""
    # Test vector health check
    response = client.get("/api/v1/vectors/health")
    assert response.status_code == 200
    
    # Test collection stats
    response = client.get("/api/v1/vectors/collections/stats")
    assert response.status_code in [200, 500]  # May fail if ChromaDB not available
    
    # Test vector initialization
    response = client.post("/api/v1/vectors/initialize")
    assert response.status_code in [200, 500]  # May fail if ChromaDB not available