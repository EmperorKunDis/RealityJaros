from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
import secrets
import logging

from src.services.auth_service import GoogleAuthenticationService
from src.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

class AuthResponse(BaseModel):
    """Authentication response model"""
    access_token: str
    token_type: str = "bearer"
    user_email: str
    user_name: Optional[str]
    expires_in: int

class AuthStatus(BaseModel):
    """Authentication status model"""
    is_authenticated: bool
    user_email: Optional[str]
    last_sync: Optional[str]

@router.get("/login")
async def initiate_google_login(request: Request):
    """
    Initiate Google OAuth 2.0 authentication flow
    
    Returns:
        Redirect response to Google authorization server
    """
    try:
        # Generate CSRF state token
        state = secrets.token_urlsafe(32)
        
        # Store state in session/cache for validation
        # In production use Redis or secure session storage
        # For now, we'll return it in response for simplicity
        
        auth_service = GoogleAuthenticationService()
        authorization_url = await auth_service.create_authorization_url(state)
        
        logger.info("Initiating Google OAuth flow")
        return {
            "authorization_url": authorization_url,
            "state": state
        }
        
    except Exception as e:
        logger.error(f"Error initiating Google login: {e}")
        raise HTTPException(status_code=500, detail="Authentication initialization failed")

@router.get("/callback")
async def google_auth_callback(request: Request, code: str, state: str):
    """
    Handle Google OAuth 2.0 callback
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        
    Returns:
        Authentication response with tokens
    """
    try:
        # TODO: Validate state parameter against stored value
        # For now, we'll skip this validation in development
        
        auth_service = GoogleAuthenticationService()
        auth_result = await auth_service.exchange_code_for_tokens(code, state)
        
        # TODO: Create JWT or session token
        # This is simplified - implement proper JWT creation
        access_token = f"jwt_token_for_{auth_result['user'].email}"
        
        response_data = AuthResponse(
            access_token=access_token,
            user_email=auth_result["user"].email,
            user_name=auth_result["user"].display_name,
            expires_in=3600
        )
        
        logger.info(f"Successfully authenticated user: {auth_result['user'].email}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in Google auth callback: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@router.get("/status")
async def get_auth_status():
    """
    Get current authentication status
    
    Returns:
        Current authentication status and user information
    """
    try:
        # TODO: Validate JWT token and get user info
        # This is simplified - implement proper JWT validation
        
        return AuthStatus(
            is_authenticated=False,
            user_email=None,
            last_sync=None
        )
        
    except Exception as e:
        logger.error(f"Error getting auth status: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")

@router.post("/logout")
async def logout():
    """
    Log out user and invalidate tokens
    
    Returns:
        Success message
    """
    try:
        # TODO: Invalidate JWT token
        # Implementation depends on token storage strategy
        
        logger.info("User successfully logged out")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.post("/refresh")
async def refresh_token():
    """
    Refresh access token
    
    Returns:
        New access token
    """
    try:
        # TODO: Refresh Google access token and create new JWT
        # This is simplified - implement proper token refresh
        
        new_token = "new_jwt_token_here"
        
        return AuthResponse(
            access_token=new_token,
            user_email="user@example.com",
            user_name="User Name",
            expires_in=3600
        )
        
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(status_code=401, detail="Token refresh failed")