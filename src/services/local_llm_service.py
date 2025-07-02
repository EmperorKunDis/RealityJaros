"""
Local LLM Service

Provides comprehensive local Large Language Model integration:
- Ollama model management and inference
- Hugging Face Transformers local models
- LLaMA.cpp integration
- Model switching and performance optimization
- Privacy-focused local AI processing
"""

import logging
import asyncio
import aiohttp
import json
import time
import psutil
import GPUtil
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import subprocess
import os
import httpx

from src.config.database import AsyncSessionLocal
from src.config.settings import settings
from src.models.user import User
from src.models.local_llm import (
    LLMModel, UserLLMPreference, LLMProvider_Configuration,
    LLMInferenceLog, ModelSwitchingRule, ModelDownloadJob,
    LLMPerformanceBenchmark, LLMProvider, ModelStatus, ModelType
)

logger = logging.getLogger(__name__)


class LocalLLMService:
    """
    Main service for local LLM management and inference
    """
    
    def __init__(self):
        self.ollama_client = None
        self.hf_models = {}  # Cache for loaded Hugging Face models
        self.current_models = {}  # Currently loaded models by type
        self.performance_monitor = PerformanceMonitor()
    
    # Model Management
    
    async def register_model(
        self,
        model_name: str,
        display_name: str,
        model_id: str,
        provider: str,
        model_type: str,
        model_config: Dict[str, Any] = None,
        model_size_gb: float = None,
        context_length: int = None
    ) -> str:
        """Register a new LLM model in the system"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if model already exists
                stmt = select(LLMModel).where(LLMModel.model_name == model_name)
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    raise ValueError(f"Model {model_name} already registered")
                
                model = LLMModel(
                    model_name=model_name,
                    display_name=display_name,
                    model_id=model_id,
                    provider=provider,
                    model_type=model_type,
                    model_config=model_config or {},
                    model_size_gb=model_size_gb,
                    context_length=context_length,
                    status=ModelStatus.AVAILABLE
                )
                
                session.add(model)
                await session.commit()
                await session.refresh(model)
                
                logger.info(f"Registered model {model_name} ({provider})")
                return str(model.id)
                
        except Exception as e:
            logger.error(f"Failed to register model: {str(e)}")
            raise
    
    async def get_available_models(
        self,
        user_id: Optional[str] = None,
        model_type: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of available models"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(LLMModel).where(LLMModel.is_enabled == True)
                
                if model_type:
                    stmt = stmt.where(LLMModel.model_type == model_type)
                if provider:
                    stmt = stmt.where(LLMModel.provider == provider)
                
                result = await session.execute(stmt)
                models = result.scalars().all()
                
                model_list = []
                for model in models:
                    model_info = {
                        "id": str(model.id),
                        "name": model.model_name,
                        "display_name": model.display_name,
                        "provider": model.provider,
                        "type": model.model_type,
                        "status": model.status,
                        "size_gb": model.model_size_gb,
                        "context_length": model.context_length,
                        "avg_response_time_ms": model.avg_response_time_ms,
                        "supported_languages": model.supported_languages
                    }
                    
                    # Add health check for loaded models
                    if model.status == ModelStatus.LOADED:
                        health = await self._check_model_health(model)
                        model_info["health"] = health
                    
                    model_list.append(model_info)
                
                return model_list
                
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            raise
    
    async def load_model(self, model_id: str) -> bool:
        """Load a model into memory for inference"""
        try:
            async with AsyncSessionLocal() as session:
                # Get model details
                stmt = select(LLMModel).where(LLMModel.id == model_id)
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()
                
                if not model:
                    raise ValueError(f"Model {model_id} not found")
                
                if model.status == ModelStatus.LOADED:
                    logger.info(f"Model {model.model_name} already loaded")
                    return True
                
                # Update status
                model.status = ModelStatus.LOADING
                await session.commit()
                
                # Load model based on provider
                success = False
                if model.provider == LLMProvider.OLLAMA:
                    success = await self._load_ollama_model(model)
                elif model.provider == LLMProvider.HUGGINGFACE:
                    success = await self._load_huggingface_model(model)
                elif model.provider == LLMProvider.LLAMA_CPP:
                    success = await self._load_llamacpp_model(model)
                
                # Update status based on loading result
                if success:
                    model.status = ModelStatus.LOADED
                    model.last_used_at = datetime.now()
                    self.current_models[model.model_type] = model
                else:
                    model.status = ModelStatus.ERROR
                
                await session.commit()
                
                logger.info(f"Model {model.model_name} loading {'successful' if success else 'failed'}")
                return success
                
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False
    
    async def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(LLMModel).where(LLMModel.id == model_id)
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()
                
                if not model:
                    raise ValueError(f"Model {model_id} not found")
                
                # Unload based on provider
                success = False
                if model.provider == LLMProvider.OLLAMA:
                    success = await self._unload_ollama_model(model)
                elif model.provider == LLMProvider.HUGGINGFACE:
                    success = await self._unload_huggingface_model(model)
                elif model.provider == LLMProvider.LLAMA_CPP:
                    success = await self._unload_llamacpp_model(model)
                
                if success:
                    model.status = ModelStatus.AVAILABLE
                    if model.model_type in self.current_models:
                        del self.current_models[model.model_type]
                
                await session.commit()
                
                logger.info(f"Model {model.model_name} unloaded")
                return success
                
        except Exception as e:
            logger.error(f"Failed to unload model: {str(e)}")
            return False
    
    # Inference Methods
    
    async def generate_chat_response(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a chat response using local LLM"""
        start_time = time.time()
        
        try:
            # Select model
            model = await self._select_model_for_user(user_id, ModelType.CHAT, model_id)
            if not model:
                raise ValueError("No suitable chat model available")
            
            # Ensure model is loaded
            if model.status != ModelStatus.LOADED:
                await self.load_model(str(model.id))
            
            # Start performance monitoring
            monitor_task = asyncio.create_task(
                self.performance_monitor.start_monitoring(str(model.id))
            )
            
            # Generate response based on provider
            response = None
            if model.provider == LLMProvider.OLLAMA:
                response = await self._ollama_chat(model, messages, parameters)
            elif model.provider == LLMProvider.HUGGINGFACE:
                response = await self._huggingface_chat(model, messages, parameters)
            elif model.provider == LLMProvider.LLAMA_CPP:
                response = await self._llamacpp_chat(model, messages, parameters)
            
            # Stop monitoring
            monitor_task.cancel()
            
            # Calculate metrics
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log inference
            await self._log_inference(
                user_id=user_id,
                model_id=str(model.id),
                request_type="chat",
                response_time_ms=response_time_ms,
                success=response is not None,
                parameters_used=parameters or {}
            )
            
            # Update model statistics
            await self._update_model_stats(model, response_time_ms, response is not None)
            
            if response:
                return {
                    "success": True,
                    "response": response,
                    "model_used": model.model_name,
                    "provider": model.provider,
                    "response_time_ms": response_time_ms
                }
            else:
                raise Exception("Model returned empty response")
                
        except Exception as e:
            # Log failed inference
            await self._log_inference(
                user_id=user_id,
                model_id=model_id or "unknown",
                request_type="chat",
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            
            # Try fallback if enabled
            user_prefs = await self._get_user_preferences(user_id)
            if user_prefs and user_prefs.enable_cloud_fallback:
                logger.warning(f"Local LLM failed, using cloud fallback: {str(e)}")
                return await self._cloud_fallback_chat(messages, user_prefs.cloud_fallback_model)
            
            raise
    
    async def generate_completion(
        self,
        user_id: str,
        prompt: str,
        model_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate text completion using local LLM"""
        start_time = time.time()
        
        try:
            # Select model
            model = await self._select_model_for_user(user_id, ModelType.COMPLETION, model_id)
            if not model:
                raise ValueError("No suitable completion model available")
            
            # Ensure model is loaded
            if model.status != ModelStatus.LOADED:
                await self.load_model(str(model.id))
            
            # Generate completion based on provider
            completion = None
            if model.provider == LLMProvider.OLLAMA:
                completion = await self._ollama_completion(model, prompt, parameters)
            elif model.provider == LLMProvider.HUGGINGFACE:
                completion = await self._huggingface_completion(model, prompt, parameters)
            elif model.provider == LLMProvider.LLAMA_CPP:
                completion = await self._llamacpp_completion(model, prompt, parameters)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log inference
            await self._log_inference(
                user_id=user_id,
                model_id=str(model.id),
                request_type="completion",
                response_time_ms=response_time_ms,
                success=completion is not None
            )
            
            if completion:
                return {
                    "success": True,
                    "completion": completion,
                    "model_used": model.model_name,
                    "provider": model.provider,
                    "response_time_ms": response_time_ms
                }
            else:
                raise Exception("Model returned empty completion")
                
        except Exception as e:
            logger.error(f"Completion generation failed: {str(e)}")
            raise
    
    async def generate_embeddings(
        self,
        user_id: str,
        texts: List[str],
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate embeddings using local model"""
        start_time = time.time()
        
        try:
            # Select embedding model
            model = await self._select_model_for_user(user_id, ModelType.EMBEDDING, model_id)
            if not model:
                raise ValueError("No suitable embedding model available")
            
            # Generate embeddings based on provider
            embeddings = None
            if model.provider == LLMProvider.OLLAMA:
                embeddings = await self._ollama_embeddings(model, texts)
            elif model.provider == LLMProvider.HUGGINGFACE:
                embeddings = await self._huggingface_embeddings(model, texts)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log inference
            await self._log_inference(
                user_id=user_id,
                model_id=str(model.id),
                request_type="embedding",
                response_time_ms=response_time_ms,
                success=embeddings is not None
            )
            
            if embeddings:
                return {
                    "success": True,
                    "embeddings": embeddings,
                    "model_used": model.model_name,
                    "response_time_ms": response_time_ms
                }
            else:
                raise Exception("Model returned empty embeddings")
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    # Provider-specific implementations
    
    async def _load_ollama_model(self, model: LLMModel) -> bool:
        """Load model using Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                # Check if Ollama is running
                try:
                    response = await client.get("http://localhost:11434/api/tags")
                    if response.status_code != 200:
                        logger.error("Ollama service not available")
                        return False
                except Exception:
                    logger.error("Cannot connect to Ollama service")
                    return False
                
                # Pull model if not available
                pull_response = await client.post(
                    "http://localhost:11434/api/pull",
                    json={"name": model.model_id},
                    timeout=300.0
                )
                
                if pull_response.status_code == 200:
                    logger.info(f"Ollama model {model.model_id} ready")
                    return True
                else:
                    logger.error(f"Failed to pull Ollama model: {pull_response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading Ollama model: {str(e)}")
            return False
    
    async def _ollama_chat(
        self,
        model: LLMModel,
        messages: List[Dict[str, str]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate chat response using Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": model.model_id,
                    "messages": messages,
                    "stream": False
                }
                
                # Add custom parameters
                if parameters:
                    payload.update(parameters)
                
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("message", {}).get("content", "")
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Ollama chat error: {str(e)}")
            raise
    
    async def _load_huggingface_model(self, model: LLMModel) -> bool:
        """Load Hugging Face model locally"""
        try:
            # This would implement local Hugging Face model loading
            # For now, return success for demonstration
            logger.info(f"Loading Hugging Face model {model.model_id}")
            
            # Simulate loading time
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading Hugging Face model: {str(e)}")
            return False
    
    async def _huggingface_chat(
        self,
        model: LLMModel,
        messages: List[Dict[str, str]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate chat response using Hugging Face Transformers"""
        try:
            # This would implement actual Hugging Face inference
            # For now, return a placeholder response
            
            prompt = self._format_chat_prompt(messages)
            
            # Simulate response generation
            await asyncio.sleep(0.5)
            
            return f"Response from {model.model_name}: {prompt[:100]}..."
            
        except Exception as e:
            logger.error(f"Hugging Face chat error: {str(e)}")
            raise
    
    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages into a single prompt"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
    
    # User Preferences and Model Selection
    
    async def _select_model_for_user(
        self,
        user_id: str,
        model_type: str,
        preferred_model_id: Optional[str] = None
    ) -> Optional[LLMModel]:
        """Select the best model for user based on preferences and availability"""
        try:
            async with AsyncSessionLocal() as session:
                # If specific model requested, try to use it
                if preferred_model_id:
                    stmt = select(LLMModel).where(
                        and_(
                            LLMModel.id == preferred_model_id,
                            LLMModel.is_enabled == True,
                            LLMModel.model_type == model_type
                        )
                    )
                    result = await session.execute(stmt)
                    model = result.scalar_one_or_none()
                    if model:
                        return model
                
                # Get user preferences
                user_prefs = await self._get_user_preferences(user_id)
                
                # Try user's default model for this type
                if user_prefs:
                    default_model_id = None
                    if model_type == ModelType.CHAT:
                        default_model_id = user_prefs.default_chat_model_id
                    elif model_type == ModelType.COMPLETION:
                        default_model_id = user_prefs.default_completion_model_id
                    elif model_type == ModelType.EMBEDDING:
                        default_model_id = user_prefs.default_embedding_model_id
                    
                    if default_model_id:
                        stmt = select(LLMModel).where(LLMModel.id == default_model_id)
                        result = await session.execute(stmt)
                        model = result.scalar_one_or_none()
                        if model and model.is_enabled:
                            return model
                
                # Fall back to any available model of the requested type
                stmt = select(LLMModel).where(
                    and_(
                        LLMModel.model_type == model_type,
                        LLMModel.is_enabled == True,
                        LLMModel.status.in_([ModelStatus.LOADED, ModelStatus.AVAILABLE])
                    )
                ).order_by(LLMModel.avg_response_time_ms.asc().nullslast())
                
                result = await session.execute(stmt)
                return result.scalars().first()
                
        except Exception as e:
            logger.error(f"Error selecting model for user: {str(e)}")
            return None
    
    async def _get_user_preferences(self, user_id: str) -> Optional[UserLLMPreference]:
        """Get user's LLM preferences"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserLLMPreference).where(UserLLMPreference.user_id == user_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return None
    
    # Logging and Monitoring
    
    async def _log_inference(
        self,
        user_id: str,
        model_id: str,
        request_type: str,
        response_time_ms: float,
        success: bool,
        parameters_used: Optional[Dict] = None,
        error_message: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None
    ):
        """Log inference request for monitoring"""
        try:
            async with AsyncSessionLocal() as session:
                log_entry = LLMInferenceLog(
                    user_id=user_id,
                    model_id=model_id,
                    request_type=request_type,
                    response_time_ms=response_time_ms,
                    success=success,
                    parameters_used=parameters_used or {},
                    error_message=error_message,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=(prompt_tokens or 0) + (completion_tokens or 0) if prompt_tokens and completion_tokens else None
                )
                
                session.add(log_entry)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log inference: {str(e)}")
    
    async def _update_model_stats(self, model: LLMModel, response_time_ms: float, success: bool):
        """Update model performance statistics"""
        try:
            async with AsyncSessionLocal() as session:
                model.total_requests += 1
                if success:
                    model.successful_requests += 1
                    
                    # Update average response time
                    if model.avg_response_time_ms:
                        model.avg_response_time_ms = (
                            (model.avg_response_time_ms * (model.successful_requests - 1) + response_time_ms) 
                            / model.successful_requests
                        )
                    else:
                        model.avg_response_time_ms = response_time_ms
                else:
                    model.failed_requests += 1
                
                model.last_used_at = datetime.now()
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update model stats: {str(e)}")
    
    async def _cloud_fallback_chat(self, messages: List[Dict[str, str]], fallback_model: str) -> Dict[str, Any]:
        """Fallback to cloud model when local models fail"""
        try:
            # This would integrate with existing OpenAI service
            logger.info(f"Using cloud fallback model: {fallback_model}")
            
            return {
                "success": True,
                "response": "Cloud fallback response (not implemented)",
                "model_used": fallback_model,
                "provider": "openai",
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Cloud fallback also failed: {str(e)}")
            raise
    
    # Placeholder methods for additional providers
    async def _load_llamacpp_model(self, model: LLMModel) -> bool:
        """Load LLaMA.cpp model"""
        # Implementation would handle LLaMA.cpp model loading
        return True
    
    async def _unload_ollama_model(self, model: LLMModel) -> bool:
        """Unload Ollama model"""
        # Ollama manages its own memory, so this is mostly a status update
        return True
    
    async def _unload_huggingface_model(self, model: LLMModel) -> bool:
        """Unload Hugging Face model"""
        # Implementation would unload from GPU/CPU memory
        return True
    
    async def _unload_llamacpp_model(self, model: LLMModel) -> bool:
        """Unload LLaMA.cpp model"""
        # Implementation would unload LLaMA.cpp model
        return True
    
    async def _check_model_health(self, model: LLMModel) -> Dict[str, Any]:
        """Check if a loaded model is healthy and responsive"""
        try:
            # Simple health check - try a small inference
            if model.provider == LLMProvider.OLLAMA:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:11434/api/generate",
                        json={"model": model.model_id, "prompt": "test", "stream": False},
                        timeout=5.0
                    )
                    return {"healthy": response.status_code == 200, "response_time": response.elapsed.total_seconds()}
            
            return {"healthy": True, "response_time": 0}
            
        except Exception as e:
            return {"healthy": False, "error": str(e)}


class PerformanceMonitor:
    """Monitor system performance during model inference"""
    
    def __init__(self):
        self.monitoring_tasks = {}
    
    async def start_monitoring(self, model_id: str):
        """Start monitoring system resources for a model"""
        try:
            # Monitor CPU, RAM, GPU usage during inference
            while True:
                await asyncio.sleep(0.1)  # Monitor every 100ms
                
                # Get system metrics
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                # Get GPU metrics if available
                gpu_usage = 0
                gpu_memory = 0
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]
                        gpu_usage = gpu.load * 100
                        gpu_memory = gpu.memoryUsed
                except:
                    pass
                
                # Store metrics (would save to database in production)
                logger.debug(f"Model {model_id} - CPU: {cpu_percent}%, RAM: {memory.percent}%, GPU: {gpu_usage}%")
                
        except asyncio.CancelledError:
            # Monitoring was stopped
            pass
        except Exception as e:
            logger.error(f"Performance monitoring error: {str(e)}")


# Global service instance
local_llm_service = LocalLLMService()