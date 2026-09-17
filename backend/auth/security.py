import os
import time
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

NEON_JWKS_URL = os.getenv("NEON_AUTH_JWKS_URL")

class CachedJWKSClient:
    """Caches JWKS keys to avoid querying Neon Auth on every incoming request."""
    def __init__(self, jwks_url: str, cache_ttl_seconds: int = 3600):
        self.jwks_url = jwks_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self.last_fetch = 0
        self.jwk_client = PyJWKClient(jwks_url)

    def get_signing_key(self, token: str):
        # Refresh client cache if TTL expired
        if time.time() - self.last_fetch > self.cache_ttl_seconds:
            self.jwk_client = PyJWKClient(self.jwks_url)
            self.last_fetch = time.time()
        return self.jwk_client.get_signing_key_from_jwt(token)

jwks_cache = CachedJWKSClient(NEON_JWKS_URL)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token = credentials.credentials
    try:
        # Get matching public key from JWKS endpoint based on JWT header 'kid'
        signing_key = jwks_cache.get_signing_key(token)
        
        # Decode and verify token signature
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            options={"verify_aud": False}
        )
        
        # Extract user ID (Neon Auth populates 'sub' or 'userId')
        user_id: str = payload.get("sub") or payload.get("userId") or payload.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed: missing user identifier ('sub' or 'userId')",
            )
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )