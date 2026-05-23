from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from app.core.config import SUPABASE_JWT_SECRET, SUPABASE_URL
import httpx
import os

security = HTTPBearer()

def get_jwks():
    url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    response = httpx.get(url)
    return response.json()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        jwks = get_jwks()
        keys = jwks.get("keys", [])
        
        payload = jwt.decode(
            token,
            keys,
            algorithms=["ES256", "HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")