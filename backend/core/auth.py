from typing import Dict, Optional
from datetime import datetime, timedelta
import jwt
import requests
from fastapi import HTTPException, status

class AuthManager:
    def __init__(self, discord_client_id: str, discord_client_secret: str, 
                 jwt_secret: str, jwt_expires_minutes: int = 60):
        self.discord_client_id = discord_client_id
        self.discord_client_secret = discord_client_secret
        self.jwt_secret = jwt_secret
        self.jwt_expires_minutes = jwt_expires_minutes
    
    def generate_discord_oauth_url(self, redirect_uri: str) -> str:
        """Generate Discord OAuth URL"""
        return (
            f"https://discord.com/api/oauth2/authorize?"
            f"client_id={self.discord_client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=identify%20guilds"
        )
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for Discord access token"""
        url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": self.discord_client_id,
            "client_secret": self.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": "identify guilds"
        }
        
        response = requests.post(url, data=data)
        return response.json()
    
    def get_discord_user(self, access_token: str) -> Dict:
        """Get user info from Discord"""
        url = "https://discord.com/api/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def get_user_guilds(self, access_token: str) -> List[Dict]:
        """Get user's guilds"""
        url = "https://discord.com/api/users/@me/guilds"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def verify_guild_role(self, user_id: str, guild_id: str, 
                         required_role: str, access_token: str) -> bool:
        """Verify user has required role in guild"""
        # This would typically use Discord's API to check roles
        # Implementation depends on your role management system
        return True  # Placeholder
    
    def create_access_token(self, user_id: str, roles: List[str]) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.jwt_expires_minutes)
        payload = {
            "user_id": user_id,
            "roles": roles,
            "exp": expire
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_access_token(self, token: str) -> Dict:
        """Verify JWT access token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
