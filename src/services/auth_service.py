from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime, timedelta

from src.config.settings import settings
from src.models.user import User
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class GoogleAuthenticationService:
    """
    Comprehensive Google Workspace authentication service
    Manages OAuth 2.0 flow, token refresh and API service creation
    """
    
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        self.scopes = settings.google_scopes
        
    async def create_authorization_url(self, state: str) -> str:
        """
        Create OAuth 2.0 authorization URL
        
        Args:
            state: CSRF protection state parameter
            
        Returns:
            Authorization URL for user redirect
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = settings.google_redirect_uri
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            logger.info(f"Created authorization URL for state: {state}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error creating authorization URL: {e}")
            raise

    async def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from callback
            state: State parameter for CSRF protection
            
        Returns:
            User information and tokens
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = settings.google_redirect_uri
            
            # Get tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user information
            user_info = await self._get_user_info(credentials)
            
            # Create or update user
            async with AsyncSessionLocal() as session:
                user = await self._create_or_update_user(session, user_info, credentials)
                await session.commit()
            
            logger.info(f"Successfully authenticated user: {user_info['email']}")
            
            return {
                "user": user,
                "credentials": {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_uri": credentials.token_uri,
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "scopes": credentials.scopes
                }
            }
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            raise

    async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """
        Get user information from Google API
        
        Args:
            credentials: Google OAuth 2.0 credentials
            
        Returns:
            User profile information
        """
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                "google_id": user_info.get("id"),
                "email": user_info.get("email"),
                "display_name": user_info.get("name"),
                "profile_picture": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False)
            }
            
        except HttpError as e:
            logger.error(f"Google API error getting user info: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise

    async def _create_or_update_user(self, session, user_info: Dict[str, Any], credentials: Credentials) -> User:
        """
        Create new user or update existing one
        
        Args:
            session: Database session
            user_info: User profile information
            credentials: Google OAuth 2.0 credentials
            
        Returns:
            User model instance
        """
        from sqlalchemy import select
        
        # Check if user exists
        stmt = select(User).where(User.email == user_info["email"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user
            user.google_id = user_info["google_id"]
            user.display_name = user_info["display_name"]
            user.profile_picture = user_info["profile_picture"]
            user.is_verified = user_info["verified_email"]
            user.last_login = datetime.utcnow()
            logger.info(f"Updated existing user: {user.email}")
        else:
            # Create new user
            user = User(
                email=user_info["email"],
                google_id=user_info["google_id"],
                display_name=user_info["display_name"],
                profile_picture=user_info["profile_picture"],
                is_verified=user_info["verified_email"],
                last_login=datetime.utcnow()
            )
            session.add(user)
            logger.info(f"Created new user: {user.email}")
        
        return user

    async def refresh_access_token(self, refresh_token: str) -> Optional[Credentials]:
        """
        Refresh expired access token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Refreshed credentials or None if refresh failed
        """
        try:
            credentials = Credentials(
                token=None,  # Will be refreshed
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret
            )
            
            credentials.refresh(Request())
            
            logger.info("Access token refreshed successfully")
            return credentials
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    async def get_gmail_service(self, credentials: Credentials):
        """
        Create Gmail API service instance
        
        Args:
            credentials: Valid Google OAuth 2.0 credentials
            
        Returns:
            Gmail API service instance
        """
        try:
            service = build('gmail', 'v1', credentials=credentials)
            logger.debug("Created Gmail API service")
            return service
            
        except Exception as e:
            logger.error(f"Error creating Gmail service: {e}")
            raise

    async def validate_credentials(self, credentials: Credentials) -> bool:
        """
        Validate if credentials are still valid
        
        Args:
            credentials: Google OAuth 2.0 credentials
            
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            service = await self.get_gmail_service(credentials)
            # Test API call
            service.users().getProfile(userId='me').execute()
            return True
            
        except Exception as e:
            logger.warning(f"Credentials validation failed: {e}")
            return False