"""
GDPR Audit Middleware

Automatically logs API access and data processing activities for GDPR compliance.
Integrates with existing FastAPI routes to provide comprehensive audit trails.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.routing import APIRoute
import time
import json

from src.services.gdpr_compliance_service import gdpr_service
from src.models.gdpr_compliance import DataProcessingPurpose, DataCategory

logger = logging.getLogger(__name__)


class GDPRAuditRoute(APIRoute):
    """
    Custom APIRoute that automatically logs GDPR-relevant activities
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Start timing
            start_time = time.time()
            
            # Extract user ID if available
            user_id = None
            try:
                # Try to get user from request state (set by auth middleware)
                if hasattr(request.state, 'user') and request.state.user:
                    user_id = str(request.state.user.id)
            except Exception:
                pass
            
            # Determine data categories and processing purpose based on endpoint
            data_categories, legal_basis = self._categorize_endpoint(request.url.path, request.method)
            
            response = None
            success = True
            error_message = None
            
            try:
                # Execute the original route handler
                response = await original_route_handler(request)
                return response
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
                
            finally:
                # Log the API access
                if self._should_log_endpoint(request.url.path):
                    try:
                        await gdpr_service.log_data_access(
                            user_id=user_id,
                            event_type="api_access",
                            action=f"{request.method}_{request.url.path.replace('/', '_').strip('_')}",
                            resource_type=self._extract_resource_type(request.url.path),
                            resource_id=self._extract_resource_id(request.url.path),
                            data_categories=data_categories,
                            legal_basis=legal_basis,
                            request=request,
                            success=success,
                            error_message=error_message
                        )
                    except Exception as audit_error:
                        logger.error(f"Failed to log GDPR audit: {audit_error}")
        
        return custom_route_handler
    
    def _should_log_endpoint(self, path: str) -> bool:
        """Determine if endpoint should be logged for GDPR compliance"""
        # Skip health checks and static endpoints
        skip_paths = ["/health", "/", "/docs", "/redoc", "/openapi.json"]
        return not any(path.startswith(skip) for skip in skip_paths)
    
    def _categorize_endpoint(self, path: str, method: str) -> tuple[list[str], str]:
        """Categorize endpoint for GDPR data categories and legal basis"""
        data_categories = []
        legal_basis = DataProcessingPurpose.LEGITIMATE_INTERESTS  # Default
        
        # Email-related endpoints
        if "/emails" in path:
            data_categories = [DataCategory.CONTACT_DATA, DataCategory.COMMUNICATION_METADATA]
            legal_basis = DataProcessingPurpose.CONSENT
        
        # User profile endpoints
        elif "/auth" in path or "/users" in path:
            data_categories = [DataCategory.BASIC_IDENTITY, DataCategory.TECHNICAL_DATA]
            legal_basis = DataProcessingPurpose.CONTRACT
        
        # Analysis endpoints
        elif "/analysis" in path:
            data_categories = [DataCategory.BEHAVIORAL_DATA, DataCategory.PROFILE_DATA]
            legal_basis = DataProcessingPurpose.CONSENT
        
        # Response generation
        elif "/responses" in path:
            data_categories = [DataCategory.COMMUNICATION_METADATA, DataCategory.BEHAVIORAL_DATA]
            legal_basis = DataProcessingPurpose.CONSENT
        
        # Vector/RAG operations
        elif "/vectors" in path:
            data_categories = [DataCategory.CONTACT_DATA, DataCategory.PROFILE_DATA]
            legal_basis = DataProcessingPurpose.CONSENT
        
        # GDPR compliance endpoints
        elif "/gdpr" in path:
            data_categories = [DataCategory.BASIC_IDENTITY]
            legal_basis = DataProcessingPurpose.LEGAL_OBLIGATION
        
        # Setup wizard
        elif "/setup-wizard" in path:
            data_categories = [DataCategory.BASIC_IDENTITY, DataCategory.BEHAVIORAL_DATA]
            legal_basis = DataProcessingPurpose.CONSENT
        
        return data_categories, legal_basis
    
    def _extract_resource_type(self, path: str) -> str:
        """Extract resource type from API path"""
        if "/emails" in path:
            return "email"
        elif "/clients" in path:
            return "client"
        elif "/responses" in path:
            return "response"
        elif "/auth" in path:
            return "authentication"
        elif "/analysis" in path:
            return "analysis"
        elif "/vectors" in path:
            return "vector_data"
        elif "/gdpr" in path:
            return "gdpr_data"
        elif "/setup-wizard" in path:
            return "setup_configuration"
        else:
            return "api_endpoint"
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from API path if available"""
        try:
            # Look for UUID patterns in path segments
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            match = re.search(uuid_pattern, path)
            if match:
                return match.group()
        except Exception:
            pass
        return None


def create_gdpr_audit_decorator():
    """
    Create a decorator for manual GDPR audit logging in service methods
    """
    def gdpr_audit(
        event_type: str,
        action: str,
        resource_type: str,
        data_categories: list[str] = None,
        legal_basis: str = DataProcessingPurpose.LEGITIMATE_INTERESTS
    ):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract user_id from arguments if available
                user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
                
                success = True
                error_message = None
                result = None
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                finally:
                    try:
                        await gdpr_service.log_data_access(
                            user_id=user_id,
                            event_type=event_type,
                            action=action,
                            resource_type=resource_type,
                            data_categories=data_categories or [],
                            legal_basis=legal_basis,
                            success=success,
                            error_message=error_message
                        )
                    except Exception as audit_error:
                        logger.error(f"Failed to log GDPR audit in decorator: {audit_error}")
            
            return wrapper
        return decorator
    return gdpr_audit


# Global GDPR audit decorator instance
gdpr_audit = create_gdpr_audit_decorator()


class GDPRComplianceMiddleware:
    """
    FastAPI middleware for GDPR compliance logging
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add GDPR compliance headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Add privacy-related headers
                    headers[b"X-Content-Type-Options"] = b"nosniff"
                    headers[b"X-Frame-Options"] = b"DENY"
                    headers[b"X-Privacy-Policy"] = b"GDPR-compliant"
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)