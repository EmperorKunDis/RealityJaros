import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_project_structure():
    """Test that all essential project files exist"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    
    # Essential files
    essential_files = [
        'src/main.py',
        'src/config/settings.py',
        'src/config/database.py',
        'src/models/user.py',
        'src/models/email.py',
        'src/models/client.py',
        'src/models/response.py',
        'src/services/response_generator.py',
        'src/services/rag_engine.py',
        'src/services/vector_db_manager.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file_path in essential_files:
        full_path = os.path.join(base_path, file_path)
        assert os.path.exists(full_path), f"Missing essential file: {file_path}"

def test_models_import():
    """Test that models can be imported"""
    try:
        from src.models.email import EmailMessage
        from src.models.client import Client
        from src.models.response import WritingStyleProfile, ResponseRule, GeneratedResponse
        from src.models.user import User
        
        # Test model instantiation
        email = EmailMessage(
            sender="test@example.com",
            subject="Test",
            body_text="Test content"
        )
        assert email.sender == "test@example.com"
        
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")

def test_response_generator_structure():
    """Test response generator service structure"""
    try:
        from src.services.response_generator import ResponseGeneratorService, ResponseGenerationResult
        
        # Test that the class has required methods
        required_methods = [
            'generate_response',
            '_determine_generation_strategy',
            '_generate_rag_response',
            '_generate_rule_based_response',
            '_generate_template_response',
            '_apply_style_matching',
            '_validate_response_quality'
        ]
        
        for method in required_methods:
            assert hasattr(ResponseGeneratorService, method), f"Missing method: {method}"
            
    except ImportError as e:
        pytest.fail(f"Failed to import ResponseGeneratorService: {e}")

def test_configuration_structure():
    """Test configuration structure"""
    try:
        from src.config.settings import Settings
        
        # Test that Settings has required attributes
        settings = Settings()
        
        required_attrs = [
            'app_name',
            'app_version',
            'debug',
            'secret_key',
            'database_url'
        ]
        
        for attr in required_attrs:
            assert hasattr(settings, attr), f"Missing configuration attribute: {attr}"
            
    except ImportError as e:
        pytest.fail(f"Failed to import Settings: {e}")

def test_api_routes_structure():
    """Test API routes structure"""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'routes')
    
    route_files = [
        'auth.py',
        'emails.py',
        'clients.py',
        'responses.py',
        'analysis.py',
        'vectors.py'
    ]
    
    for route_file in route_files:
        route_path = os.path.join(base_path, route_file)
        assert os.path.exists(route_path), f"Missing route file: {route_file}"

def test_services_structure():
    """Test services structure"""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'services')
    
    service_files = [
        'response_generator.py',
        'rag_engine.py',
        'vector_db_manager.py',
        'email_analyzer.py',
        'client_analyzer.py',
        'style_analyzer.py',
        'topic_analyzer.py'
    ]
    
    for service_file in service_files:
        service_path = os.path.join(base_path, service_file)
        assert os.path.exists(service_path), f"Missing service file: {service_file}"

def test_database_models_completeness():
    """Test that database models have required fields"""
    try:
        from src.models.email import EmailMessage
        from src.models.client import Client
        from src.models.response import WritingStyleProfile, ResponseRule
        
        # Test EmailMessage fields
        email_fields = ['id', 'sender', 'subject', 'body_text', 'received_at']
        for field in email_fields:
            assert hasattr(EmailMessage, field), f"EmailMessage missing field: {field}"
        
        # Test Client fields
        client_fields = ['id', 'user_id', 'client_name', 'email_address']
        for field in client_fields:
            assert hasattr(Client, field), f"Client missing field: {field}"
        
        # Test WritingStyleProfile fields
        style_fields = ['user_id', 'formality_score', 'common_phrases']
        for field in style_fields:
            assert hasattr(WritingStyleProfile, field), f"WritingStyleProfile missing field: {field}"
        
    except ImportError as e:
        pytest.fail(f"Failed to import database models: {e}")

def test_response_generation_classes():
    """Test response generation classes exist and have proper structure"""
    try:
        from src.services.response_generator import ResponseGenerationResult
        
        # Test ResponseGenerationResult structure
        required_fields = [
            'response_text',
            'response_type',
            'confidence_score',
            'relevance_score',
            'style_match_score',
            'generation_time_ms',
            'model_used',
            'tokens_used',
            'context_sources'
        ]
        
        # Create test instance
        result = ResponseGenerationResult(
            response_text="Test response",
            response_type="test",
            confidence_score=0.8,
            relevance_score=0.7,
            style_match_score=0.6,
            generation_time_ms=100,
            model_used="test_model",
            tokens_used=10,
            context_sources=[]
        )
        
        for field in required_fields:
            assert hasattr(result, field), f"ResponseGenerationResult missing field: {field}"
            
    except ImportError as e:
        pytest.fail(f"Failed to import response generation classes: {e}")

def test_requirements_file():
    """Test that requirements.txt contains essential packages"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    requirements_path = os.path.join(base_path, 'requirements.txt')
    
    assert os.path.exists(requirements_path), "requirements.txt file missing"
    
    with open(requirements_path, 'r') as f:
        requirements = f.read().lower()
    
    essential_packages = [
        'fastapi',
        'sqlalchemy',
        'pydantic',
        'langchain',
        'chromadb',
        'openai',
        'sentence-transformers'
    ]
    
    for package in essential_packages:
        assert package in requirements, f"Missing essential package in requirements.txt: {package}"

def test_docker_configuration():
    """Test Docker configuration exists"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    
    docker_files = [
        'docker/Dockerfile',
        'docker/docker-compose.yml'
    ]
    
    for docker_file in docker_files:
        docker_path = os.path.join(base_path, docker_file)
        assert os.path.exists(docker_path), f"Missing Docker file: {docker_file}"

def test_documentation_exists():
    """Test that documentation files exist"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    
    doc_files = [
        'README.md',
        'DesignDocument.md'
    ]
    
    for doc_file in doc_files:
        doc_path = os.path.join(base_path, doc_file)
        assert os.path.exists(doc_path), f"Missing documentation file: {doc_file}"
        
        # Check that files are not empty
        with open(doc_path, 'r') as f:
            content = f.read().strip()
            assert len(content) > 100, f"Documentation file too short: {doc_file}"

def test_test_structure():
    """Test that test structure is complete"""
    test_dir = os.path.dirname(__file__)
    
    test_files = [
        'test_basic_functionality.py',
        'test_response_generator.py',
        'test_rag_engine.py',
        'test_vector_db_manager.py',
        'test_email_analyzer.py',
        'test_integration.py',
        'test_api_endpoints.py'
    ]
    
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        assert os.path.exists(test_path), f"Missing test file: {test_file}"

def test_scripts_exist():
    """Test that utility scripts exist"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    scripts_dir = os.path.join(base_path, 'scripts')
    
    assert os.path.exists(scripts_dir), "scripts directory missing"
    
    script_files = [
        'deployment_verification.py'
    ]
    
    for script_file in script_files:
        script_path = os.path.join(scripts_dir, script_file)
        assert os.path.exists(script_path), f"Missing script file: {script_file}"