"""
Local LLM Integration Models

Database models for local Large Language Model integration including:
- Model management and configuration
- Ollama integration
- Hugging Face local models
- LLaMA and other open-source models
- Performance monitoring and switching
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from src.config.database import Base


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LLAMA_CPP = "llama_cpp"
    TRANSFORMERS = "transformers"
    OOBABOOGA = "oobabooga"


class ModelStatus(str, Enum):
    """Model status"""
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    UNLOADED = "unloaded"


class ModelType(str, Enum):
    """Type of model function"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"


class LLMModel(Base):
    """
    Local LLM model configuration and metadata
    """
    __tablename__ = "llm_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Model identification
    model_name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    model_id = Column(String(255), nullable=False)  # Provider-specific model ID
    provider = Column(String(50), nullable=False)  # LLMProvider enum
    model_type = Column(String(50), nullable=False)  # ModelType enum
    
    # Model configuration
    model_config = Column(JSON, default={})  # Provider-specific configuration
    default_parameters = Column(JSON, default={})  # Default inference parameters
    
    # Model metadata
    model_size_gb = Column(Float, nullable=True)
    context_length = Column(Integer, nullable=True)
    supported_languages = Column(JSON, default=["en"])
    
    # Status and health
    status = Column(String(50), default=ModelStatus.AVAILABLE)  # ModelStatus enum
    is_enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Performance metrics
    avg_response_time_ms = Column(Float, nullable=True)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    
    # Resource requirements
    min_ram_gb = Column(Float, nullable=True)
    min_vram_gb = Column(Float, nullable=True)
    recommended_cpu_cores = Column(Integer, nullable=True)
    
    # Installation and paths
    installation_path = Column(String(500), nullable=True)
    model_file_path = Column(String(500), nullable=True)
    download_url = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user_preferences = relationship("UserLLMPreference", back_populates="model")
    inference_logs = relationship("LLMInferenceLog", back_populates="model")


class UserLLMPreference(Base):
    """
    User preferences for LLM model selection and configuration
    """
    __tablename__ = "user_llm_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Model preferences by use case
    default_chat_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=True)
    default_completion_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=True)
    default_embedding_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=True)
    
    # Fallback configuration
    enable_cloud_fallback = Column(Boolean, default=True)
    cloud_fallback_model = Column(String(100), default="gpt-3.5-turbo")
    
    # Performance preferences
    preferred_response_time_ms = Column(Integer, default=5000)
    max_context_length = Column(Integer, nullable=True)
    enable_model_switching = Column(Boolean, default=True)
    
    # Privacy settings
    prefer_local_models = Column(Boolean, default=True)
    allow_telemetry = Column(Boolean, default=False)
    
    # Custom parameters
    custom_parameters = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="llm_preferences")
    model = relationship("LLMModel", back_populates="user_preferences", foreign_keys=[default_chat_model_id])


class LLMProvider_Configuration(Base):
    """
    Configuration for different LLM providers (Ollama, Hugging Face, etc.)
    """
    __tablename__ = "llm_provider_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Provider details
    provider_name = Column(String(50), nullable=False)  # LLMProvider enum
    provider_version = Column(String(50), nullable=True)
    
    # Connection configuration
    base_url = Column(String(500), nullable=True)  # For Ollama, Oobabooga, etc.
    api_key = Column(String(255), nullable=True)  # For Hugging Face API
    timeout_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    
    # Provider-specific settings
    provider_config = Column(JSON, default={})
    
    # Status
    is_enabled = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    
    # Installation info
    installation_path = Column(String(500), nullable=True)
    executable_path = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class LLMInferenceLog(Base):
    """
    Log of LLM inference requests for monitoring and optimization
    """
    __tablename__ = "llm_inference_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=False)
    
    # Request details
    request_type = Column(String(50), nullable=False)  # "chat", "completion", "embedding"
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Float, nullable=False)
    queue_time_ms = Column(Float, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Resource usage
    memory_usage_mb = Column(Float, nullable=True)
    gpu_memory_usage_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    
    # Quality metrics
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Request context
    use_case = Column(String(100), nullable=True)  # "email_response", "analysis", etc.
    parameters_used = Column(JSON, default={})
    
    # Metadata
    timestamp = Column(DateTime, default=func.now())
    session_id = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User")
    model = relationship("LLMModel", back_populates="inference_logs")


class ModelSwitchingRule(Base):
    """
    Rules for automatic model switching based on context and performance
    """
    __tablename__ = "model_switching_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Rule configuration
    rule_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=1)  # Higher number = higher priority
    
    # Trigger conditions
    trigger_conditions = Column(JSON, nullable=False)  # Conditions for switching
    
    # Model selection
    target_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=False)
    fallback_model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=True)
    
    # Rule settings
    is_active = Column(Boolean, default=True)
    max_daily_switches = Column(Integer, nullable=True)
    cooldown_minutes = Column(Integer, default=5)
    
    # Statistics
    times_triggered = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    target_model = relationship("LLMModel", foreign_keys=[target_model_id])
    fallback_model = relationship("LLMModel", foreign_keys=[fallback_model_id])


class ModelDownloadJob(Base):
    """
    Track model download and installation jobs
    """
    __tablename__ = "model_download_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=False)
    
    # Job details
    job_type = Column(String(50), nullable=False)  # "download", "install", "update"
    status = Column(String(50), nullable=False)  # "pending", "running", "completed", "failed"
    
    # Progress tracking
    progress_percent = Column(Float, default=0.0)
    bytes_downloaded = Column(Integer, default=0)
    total_bytes = Column(Integer, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Results
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    installation_path = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User")
    model = relationship("LLMModel")


class LLMPerformanceBenchmark(Base):
    """
    Performance benchmarks for different models and hardware configurations
    """
    __tablename__ = "llm_performance_benchmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("llm_models.id"), nullable=False)
    
    # Hardware configuration
    cpu_model = Column(String(255), nullable=True)
    ram_gb = Column(Float, nullable=True)
    gpu_model = Column(String(255), nullable=True)
    gpu_vram_gb = Column(Float, nullable=True)
    
    # Benchmark metrics
    tokens_per_second = Column(Float, nullable=True)
    first_token_latency_ms = Column(Float, nullable=True)
    memory_usage_gb = Column(Float, nullable=True)
    power_consumption_watts = Column(Float, nullable=True)
    
    # Test configuration
    prompt_length = Column(Integer, nullable=True)
    response_length = Column(Integer, nullable=True)
    batch_size = Column(Integer, default=1)
    temperature = Column(Float, default=0.7)
    
    # Quality metrics
    perplexity_score = Column(Float, nullable=True)
    bleu_score = Column(Float, nullable=True)
    
    # Metadata
    benchmark_date = Column(DateTime, default=func.now())
    benchmark_version = Column(String(50), nullable=True)
    
    # Relationships
    model = relationship("LLMModel")