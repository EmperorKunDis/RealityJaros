"""
Local LLM Setup Service

Provides automated setup and configuration for popular local LLM models:
- Ollama model auto-configuration
- Hugging Face model downloads
- Model performance benchmarking
- Quick-start setup workflows
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.services.local_llm_service import local_llm_service
from src.models.local_llm import LLMProvider, ModelType, ModelStatus

logger = logging.getLogger(__name__)


class LocalLLMSetupService:
    """
    Service for automated local LLM setup and configuration
    """
    
    def __init__(self):
        self.recommended_models = self._get_recommended_models()
    
    def _get_recommended_models(self) -> List[Dict[str, Any]]:
        """Get list of recommended models for different use cases"""
        return [
            {
                "name": "llama2_7b_chat",
                "display_name": "LLaMA 2 7B Chat",
                "model_id": "llama2:7b-chat",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.CHAT,
                "size_gb": 3.8,
                "context_length": 4096,
                "use_case": "General chat and conversation",
                "languages": ["en", "es", "fr", "de"],
                "recommended_for": ["beginners", "general_use"],
                "min_ram_gb": 8,
                "min_vram_gb": 4
            },
            {
                "name": "codellama_7b",
                "display_name": "Code Llama 7B",
                "model_id": "codellama:7b",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.COMPLETION,
                "size_gb": 3.8,
                "context_length": 4096,
                "use_case": "Code generation and analysis",
                "languages": ["code"],
                "recommended_for": ["developers", "code_analysis"],
                "min_ram_gb": 8,
                "min_vram_gb": 4
            },
            {
                "name": "mistral_7b",
                "display_name": "Mistral 7B",
                "model_id": "mistral:7b",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.CHAT,
                "size_gb": 4.1,
                "context_length": 8192,
                "use_case": "Fast, efficient chat responses",
                "languages": ["en", "fr", "es", "de", "it"],
                "recommended_for": ["performance", "multilingual"],
                "min_ram_gb": 8,
                "min_vram_gb": 4
            },
            {
                "name": "nomic_embed",
                "display_name": "Nomic Embed Text",
                "model_id": "nomic-embed-text",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.EMBEDDING,
                "size_gb": 0.3,
                "context_length": 2048,
                "use_case": "Text embeddings for RAG",
                "languages": ["en"],
                "recommended_for": ["embeddings", "rag"],
                "min_ram_gb": 4,
                "min_vram_gb": 1
            },
            {
                "name": "llama2_13b_chat",
                "display_name": "LLaMA 2 13B Chat",
                "model_id": "llama2:13b-chat",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.CHAT,
                "size_gb": 7.3,
                "context_length": 4096,
                "use_case": "Higher quality chat responses",
                "languages": ["en", "es", "fr", "de"],
                "recommended_for": ["quality", "advanced_use"],
                "min_ram_gb": 16,
                "min_vram_gb": 8
            },
            {
                "name": "dolphin_mistral",
                "display_name": "Dolphin Mistral 7B",
                "model_id": "dolphin-mistral:7b",
                "provider": LLMProvider.OLLAMA,
                "model_type": ModelType.CHAT,
                "size_gb": 4.1,
                "context_length": 8192,
                "use_case": "Uncensored helpful assistant",
                "languages": ["en"],
                "recommended_for": ["creative", "uncensored"],
                "min_ram_gb": 8,
                "min_vram_gb": 4
            }
        ]
    
    async def quick_start_setup(self, user_id: str, use_case: str = "general") -> Dict[str, Any]:
        """
        Quick setup for local LLM based on use case
        
        Args:
            user_id: User ID
            use_case: "general", "development", "multilingual", "performance"
        """
        try:
            setup_result = {
                "user_id": user_id,
                "use_case": use_case,
                "models_configured": [],
                "steps_completed": [],
                "recommendations": [],
                "estimated_setup_time_minutes": 0
            }
            
            # Get recommended models for use case
            recommended = self._get_models_for_use_case(use_case)
            
            setup_result["steps_completed"].append({
                "step": "model_selection",
                "description": f"Selected {len(recommended)} models for {use_case} use case",
                "models": [m["name"] for m in recommended]
            })
            
            # Register recommended models
            for model_config in recommended:
                try:
                    model_id = await local_llm_service.register_model(
                        model_name=model_config["name"],
                        display_name=model_config["display_name"],
                        model_id=model_config["model_id"],
                        provider=model_config["provider"],
                        model_type=model_config["model_type"],
                        model_config={
                            "use_case": model_config["use_case"],
                            "languages": model_config["languages"],
                            "recommended_for": model_config["recommended_for"]
                        },
                        model_size_gb=model_config["size_gb"],
                        context_length=model_config["context_length"]
                    )
                    
                    setup_result["models_configured"].append({
                        "model_id": model_id,
                        "name": model_config["name"],
                        "status": "registered"
                    })
                    
                except Exception as e:
                    logger.warning(f"Model {model_config['name']} already registered or error: {str(e)}")
            
            setup_result["steps_completed"].append({
                "step": "model_registration",
                "description": f"Registered {len(setup_result['models_configured'])} models"
            })
            
            # Generate user preferences
            await self._setup_user_preferences(user_id, recommended)
            
            setup_result["steps_completed"].append({
                "step": "user_preferences",
                "description": "Configured default model preferences"
            })
            
            # Add recommendations
            setup_result["recommendations"] = self._generate_setup_recommendations(use_case)
            setup_result["estimated_setup_time_minutes"] = self._estimate_setup_time(recommended)
            
            logger.info(f"Quick start setup completed for user {user_id}, use case: {use_case}")
            return setup_result
            
        except Exception as e:
            logger.error(f"Quick start setup failed: {str(e)}")
            raise
    
    def _get_models_for_use_case(self, use_case: str) -> List[Dict[str, Any]]:
        """Get recommended models for specific use case"""
        if use_case == "general":
            return [m for m in self.recommended_models if "general_use" in m["recommended_for"]]
        elif use_case == "development":
            return [m for m in self.recommended_models if any(r in ["developers", "code_analysis"] for r in m["recommended_for"])]
        elif use_case == "multilingual":
            return [m for m in self.recommended_models if "multilingual" in m["recommended_for"] or len(m["languages"]) > 2]
        elif use_case == "performance":
            return [m for m in self.recommended_models if "performance" in m["recommended_for"]]
        else:
            # Default to general use
            return [m for m in self.recommended_models if "beginners" in m["recommended_for"]]
    
    async def _setup_user_preferences(self, user_id: str, models: List[Dict[str, Any]]):
        """Setup default user preferences based on recommended models"""
        try:
            # This would create UserLLMPreference record with defaults
            # For now, just log the setup
            
            chat_models = [m for m in models if m["model_type"] == ModelType.CHAT]
            completion_models = [m for m in models if m["model_type"] == ModelType.COMPLETION]
            embedding_models = [m for m in models if m["model_type"] == ModelType.EMBEDDING]
            
            preferences = {
                "default_chat_model": chat_models[0]["name"] if chat_models else None,
                "default_completion_model": completion_models[0]["name"] if completion_models else None,
                "default_embedding_model": embedding_models[0]["name"] if embedding_models else None,
                "enable_cloud_fallback": True,
                "prefer_local_models": True
            }
            
            logger.info(f"Setup user preferences for {user_id}: {preferences}")
            
        except Exception as e:
            logger.error(f"Error setting up user preferences: {str(e)}")
    
    def _generate_setup_recommendations(self, use_case: str) -> List[Dict[str, str]]:
        """Generate setup recommendations based on use case"""
        base_recommendations = [
            {
                "type": "installation",
                "title": "Install Ollama",
                "description": "Download and install Ollama from https://ollama.ai for local model management",
                "priority": "high"
            },
            {
                "type": "hardware",
                "title": "Check System Requirements",
                "description": "Ensure you have at least 8GB RAM and 10GB free disk space",
                "priority": "high"
            },
            {
                "type": "network",
                "title": "Stable Internet Connection",
                "description": "Models need to be downloaded initially, ensure stable connection",
                "priority": "medium"
            }
        ]
        
        use_case_recommendations = {
            "general": [
                {
                    "type": "model",
                    "title": "Start with LLaMA 2 7B",
                    "description": "Good balance of quality and resource usage for general chat",
                    "priority": "high"
                }
            ],
            "development": [
                {
                    "type": "model",
                    "title": "Use Code Llama",
                    "description": "Specialized for code generation and analysis tasks",
                    "priority": "high"
                },
                {
                    "type": "integration",
                    "title": "IDE Integration",
                    "description": "Consider integrating with your IDE for code completion",
                    "priority": "medium"
                }
            ],
            "multilingual": [
                {
                    "type": "model",
                    "title": "Mistral for Multilingual",
                    "description": "Good support for multiple European languages",
                    "priority": "high"
                }
            ],
            "performance": [
                {
                    "type": "hardware",
                    "title": "GPU Acceleration",
                    "description": "Consider GPU acceleration for faster inference",
                    "priority": "medium"
                }
            ]
        }
        
        return base_recommendations + use_case_recommendations.get(use_case, [])
    
    def _estimate_setup_time(self, models: List[Dict[str, Any]]) -> int:
        """Estimate setup time in minutes based on models"""
        base_time = 5  # Base setup time
        
        for model in models:
            # Estimate download time based on model size (assuming 10MB/s)
            size_gb = model.get("size_gb", 1)
            download_time = (size_gb * 1024) / (10 * 60)  # Convert to minutes
            base_time += download_time
        
        return int(base_time)
    
    async def benchmark_model(self, model_id: str, test_prompts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Benchmark a model's performance
        
        Args:
            model_id: Model ID to benchmark
            test_prompts: Optional custom test prompts
        """
        try:
            if not test_prompts:
                test_prompts = [
                    "Hello, how are you?",
                    "Explain quantum computing in simple terms.",
                    "Write a short story about a robot.",
                    "What is the capital of France?",
                    "Generate a Python function to calculate fibonacci numbers."
                ]
            
            benchmark_results = {
                "model_id": model_id,
                "test_count": len(test_prompts),
                "results": [],
                "summary": {}
            }
            
            total_time = 0
            successful_tests = 0
            
            for i, prompt in enumerate(test_prompts):
                try:
                    start_time = time.time()
                    
                    # Run inference
                    result = await local_llm_service.generate_completion(
                        user_id="benchmark",
                        prompt=prompt,
                        model_id=model_id
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    total_time += response_time
                    successful_tests += 1
                    
                    benchmark_results["results"].append({
                        "test_index": i,
                        "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                        "response_time_ms": response_time,
                        "success": True,
                        "response_length": len(result.get("completion", ""))
                    })
                    
                except Exception as e:
                    benchmark_results["results"].append({
                        "test_index": i,
                        "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                        "success": False,
                        "error": str(e)
                    })
            
            # Calculate summary statistics
            if successful_tests > 0:
                benchmark_results["summary"] = {
                    "average_response_time_ms": total_time / successful_tests,
                    "success_rate": successful_tests / len(test_prompts),
                    "total_successful_tests": successful_tests,
                    "total_failed_tests": len(test_prompts) - successful_tests
                }
            
            logger.info(f"Benchmark completed for model {model_id}: {benchmark_results['summary']}")
            return benchmark_results
            
        except Exception as e:
            logger.error(f"Benchmark failed for model {model_id}: {str(e)}")
            raise
    
    async def health_check_all_models(self) -> Dict[str, Any]:
        """Run health check on all registered models"""
        try:
            models = await local_llm_service.get_available_models()
            
            health_results = {
                "total_models": len(models),
                "healthy_models": 0,
                "unhealthy_models": 0,
                "model_status": []
            }
            
            for model in models:
                try:
                    # Simple health check - try to load model
                    if model["status"] != ModelStatus.LOADED:
                        load_success = await local_llm_service.load_model(model["id"])
                        status = "healthy" if load_success else "unhealthy"
                    else:
                        status = "healthy"
                    
                    if status == "healthy":
                        health_results["healthy_models"] += 1
                    else:
                        health_results["unhealthy_models"] += 1
                    
                    health_results["model_status"].append({
                        "model_id": model["id"],
                        "model_name": model["name"],
                        "status": status,
                        "provider": model["provider"],
                        "type": model["type"]
                    })
                    
                except Exception as e:
                    health_results["unhealthy_models"] += 1
                    health_results["model_status"].append({
                        "model_id": model["id"],
                        "model_name": model["name"],
                        "status": "error",
                        "error": str(e)
                    })
            
            logger.info(f"Health check completed: {health_results['healthy_models']}/{health_results['total_models']} models healthy")
            return health_results
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise


# Global setup service instance
local_llm_setup = LocalLLMSetupService()