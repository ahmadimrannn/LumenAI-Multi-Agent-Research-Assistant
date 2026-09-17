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
    def __init__(self, jwks_url: str | None, cache_ttl_seconds: int = 3600):
        self.jwks_url = jwks_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self.last_fetch = 0
        self.jwk_client: PyJWKClient | None = None

    def get_signing_key(self, token: str):
        # Retrieve or refresh JWKS URL dynamically if missing at module import
        url = self.jwks_url or os.getenv("NEON_AUTH_JWKS_URL")
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="NEON_AUTH_JWKS_URL environment variable is not set.",
            )

        # Lazy initialize or refresh client cache if TTL expired
        if self.jwk_client is None or (time.time() - self.last_fetch > self.cache_ttl_seconds):
            try:
                self.jwk_client = PyJWKClient(url)
                self.last_fetch = time.time()
            except Exception as err:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize JWKS Client from URL: {str(err)}",
                )

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