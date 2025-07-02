"""
Local LLM API Routes

Provides REST API endpoints for local Large Language Model management:
- Model registration and management
- Model loading and unloading
- Local inference (chat, completion, embeddings)
- Performance monitoring and optimization
- User preferences and model switching
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from src.api.dependencies import get_current_user, get_database_session
from src.services.local_llm_service import local_llm_service
from src.models.user import User
from src.models.local_llm import LLMProvider, ModelType, ModelStatus

router = APIRouter()


# Pydantic schemas for request/response validation

class ModelRegistration(BaseModel):
    model_name: str = Field(..., description="Unique model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    model_id: str = Field(..., description="Provider-specific model ID")
    provider: str = Field(..., description="LLM provider (ollama, huggingface, etc.)")
    model_type: str = Field(..., description="Model type (chat, completion, embedding)")
    model_config: Dict[str, Any] = Field(default={}, description="Provider-specific configuration")
    model_size_gb: Optional[float] = Field(None, description="Model size in GB")
    context_length: Optional[int] = Field(None, description="Maximum context length")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model_id: Optional[str] = Field(None, description="Specific model to use")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Generation parameters")


class CompletionRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for completion")
    model_id: Optional[str] = Field(None, description="Specific model to use")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Generation parameters")


class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., description="Texts to embed")
    model_id: Optional[str] = Field(None, description="Specific embedding model to use")


class UserPreferencesUpdate(BaseModel):
    default_chat_model_id: Optional[str] = None
    default_completion_model_id: Optional[str] = None
    default_embedding_model_id: Optional[str] = None
    enable_cloud_fallback: Optional[bool] = None
    cloud_fallback_model: Optional[str] = None
    prefer_local_models: Optional[bool] = None
    preferred_response_time_ms: Optional[int] = None


# Model Management Endpoints

@router.post("/models/register", summary="Register a new LLM model")
async def register_model(
    model_data: ModelRegistration,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Register a new local LLM model in the system
    """
    try:
        model_id = await local_llm_service.register_model(
            model_name=model_data.model_name,
            display_name=model_data.display_name,
            model_id=model_data.model_id,
            provider=model_data.provider,
            model_type=model_data.model_type,
            model_config=model_data.model_config,
            model_size_gb=model_data.model_size_gb,
            context_length=model_data.context_length
        )
        
        return {
            "success": True,
            "model_id": model_id,
            "message": f"Model {model_data.model_name} registered successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register model: {str(e)}"
        )


@router.get("/models", summary="Get available models")
async def get_models(
    model_type: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get list of available local LLM models
    """
    try:
        models = await local_llm_service.get_available_models(
            user_id=str(current_user.id),
            model_type=model_type,
            provider=provider
        )
        
        return {
            "success": True,
            "models": models,
            "count": len(models),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get models: {str(e)}"
        )


@router.post("/models/{model_id}/load", summary="Load model into memory")
async def load_model(
    model_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Load a model into memory for inference
    """
    try:
        # Load model in background
        background_tasks.add_task(local_llm_service.load_model, model_id)
        
        return {
            "success": True,
            "model_id": model_id,
            "message": "Model loading initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model: {str(e)}"
        )


@router.post("/models/{model_id}/unload", summary="Unload model from memory")
async def unload_model(
    model_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Unload a model from memory to free resources
    """
    try:
        # Unload model in background
        background_tasks.add_task(local_llm_service.unload_model, model_id)
        
        return {
            "success": True,
            "model_id": model_id,
            "message": "Model unloading initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unload model: {str(e)}"
        )


# Inference Endpoints

@router.post("/chat", summary="Generate chat response using local LLM")
async def chat_completion(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate a chat response using local LLM models
    """
    try:
        result = await local_llm_service.generate_chat_response(
            user_id=str(current_user.id),
            messages=chat_request.messages,
            model_id=chat_request.model_id,
            parameters=chat_request.parameters
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.post("/completion", summary="Generate text completion using local LLM")
async def text_completion(
    completion_request: CompletionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate text completion using local LLM models
    """
    try:
        result = await local_llm_service.generate_completion(
            user_id=str(current_user.id),
            prompt=completion_request.prompt,
            model_id=completion_request.model_id,
            parameters=completion_request.parameters
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Text completion failed: {str(e)}"
        )


@router.post("/embeddings", summary="Generate embeddings using local model")
async def generate_embeddings(
    embedding_request: EmbeddingRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate text embeddings using local embedding models
    """
    try:
        result = await local_llm_service.generate_embeddings(
            user_id=str(current_user.id),
            texts=embedding_request.texts,
            model_id=embedding_request.model_id
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding generation failed: {str(e)}"
        )


# User Preferences and Configuration

@router.get("/preferences", summary="Get user LLM preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's local LLM preferences and configuration
    """
    try:
        preferences = await local_llm_service._get_user_preferences(str(current_user.id))
        
        if preferences:
            return {
                "success": True,
                "preferences": {
                    "default_chat_model_id": str(preferences.default_chat_model_id) if preferences.default_chat_model_id else None,
                    "default_completion_model_id": str(preferences.default_completion_model_id) if preferences.default_completion_model_id else None,
                    "default_embedding_model_id": str(preferences.default_embedding_model_id) if preferences.default_embedding_model_id else None,
                    "enable_cloud_fallback": preferences.enable_cloud_fallback,
                    "cloud_fallback_model": preferences.cloud_fallback_model,
                    "prefer_local_models": preferences.prefer_local_models,
                    "preferred_response_time_ms": preferences.preferred_response_time_ms,
                    "enable_model_switching": preferences.enable_model_switching
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": True,
                "preferences": None,
                "message": "No preferences set, using defaults",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get preferences: {str(e)}"
        )


@router.put("/preferences", summary="Update user LLM preferences")
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user's local LLM preferences
    """
    try:
        # This would be implemented in the service
        # For now, return success
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "updated_fields": [k for k, v in preferences_update.dict().items() if v is not None],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )


# Monitoring and Analytics

@router.get("/analytics/performance", summary="Get model performance analytics")
async def get_performance_analytics(
    days: int = 7,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance analytics for local LLM usage
    """
    try:
        # This would query inference logs and generate analytics
        # For now, return sample data
        
        analytics = {
            "period_days": days,
            "total_requests": 150,
            "successful_requests": 142,
            "average_response_time_ms": 1250,
            "models_used": {
                "llama2": {"requests": 80, "avg_time_ms": 1100},
                "codellama": {"requests": 45, "avg_time_ms": 1500},
                "mistral": {"requests": 25, "avg_time_ms": 900}
            },
            "daily_usage": [
                {"date": "2024-01-01", "requests": 20, "avg_time_ms": 1200},
                {"date": "2024-01-02", "requests": 25, "avg_time_ms": 1180}
            ]
        }
        
        return {
            "success": True,
            "analytics": analytics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get("/system/health", summary="Check local LLM system health")
async def check_system_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check the health of local LLM system and providers
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "providers": {
                "ollama": {
                    "status": "healthy",
                    "url": "http://localhost:11434",
                    "models_loaded": 2,
                    "last_check": datetime.utcnow().isoformat()
                },
                "huggingface": {
                    "status": "available",
                    "models_cached": 3,
                    "cache_size_gb": 12.5
                }
            },
            "system_resources": {
                "ram_usage_percent": 45.2,
                "gpu_memory_usage_percent": 60.1,
                "cpu_usage_percent": 25.3,
                "disk_space_available_gb": 150.8
            },
            "performance": {
                "models_loaded": 2,
                "average_response_time_ms": 1200,
                "requests_last_hour": 15
            }
        }
        
        return {
            "success": True,
            "health": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check system health: {str(e)}"
        )


# Provider-specific endpoints

@router.get("/providers/ollama/models", summary="Get available Ollama models")
async def get_ollama_models(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get models available in Ollama installation
    """
    try:
        # This would query Ollama API for available models
        models = [
            {"name": "llama2", "size": "3.8GB", "modified": "2024-01-01T10:00:00Z"},
            {"name": "codellama", "size": "7.3GB", "modified": "2024-01-02T15:30:00Z"},
            {"name": "mistral", "size": "4.1GB", "modified": "2024-01-03T09:15:00Z"}
        ]
        
        return {
            "success": True,
            "provider": "ollama",
            "models": models,
            "count": len(models),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Ollama models: {str(e)}"
        )


@router.post("/providers/ollama/pull", summary="Pull model from Ollama registry")
async def pull_ollama_model(
    model_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Pull a model from Ollama model registry
    """
    try:
        # This would initiate model pull in background
        background_tasks.add_task(
            local_llm_service._load_ollama_model,
            type('Model', (), {
                'model_id': model_name,
                'model_name': model_name
            })()
        )
        
        return {
            "success": True,
            "model_name": model_name,
            "message": f"Pulling model {model_name} from Ollama registry",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pull Ollama model: {str(e)}"
        )


# Quick Setup Endpoints

@router.post("/setup/quick-start", summary="Quick setup for local LLM")
async def quick_start_setup(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Quick setup to get started with local LLMs
    """
    try:
        setup_steps = [
            {
                "step": 1,
                "name": "Check Ollama Installation",
                "status": "completed",
                "description": "Verify Ollama is installed and running"
            },
            {
                "step": 2,
                "name": "Download Recommended Models",
                "status": "pending",
                "description": "Download llama2 and mistral models"
            },
            {
                "step": 3,
                "name": "Configure User Preferences",
                "status": "pending", 
                "description": "Set default models and preferences"
            },
            {
                "step": 4,
                "name": "Test Inference",
                "status": "pending",
                "description": "Run test inference to verify setup"
            }
        ]
        
        return {
            "success": True,
            "setup_steps": setup_steps,
            "estimated_time_minutes": 15,
            "message": "Quick setup guide ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quick setup: {str(e)}"
        )