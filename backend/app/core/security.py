from datetime import datetime, timedelta
from typing import Dict, Any

import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, status

from .config import settings


def create_access_token(
    user_id: int,
    factory_id: int,
    factory_slug: str,
    role: str
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID (becomes 'sub' in token)
        factory_id: Factory ID for isolation
        factory_slug: Factory slug for MQTT topics
        role: User role (super_admin, admin)
    
    Returns:
        Encoded JWT token string
    """
    now = datetime.utcnow()
    expires = now + timedelta(hours=settings.jwt_expiry_hours)
    
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "factory_id": factory_id,
        "factory_slug": factory_slug,
        "role": role,
        "iat": now,
        "exp": expires,
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload dictionary
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def hash_password(plain: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        plain: Plain text password
    
    Returns:
        Hashed password string
    """
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain: Plain text password
        hashed: Hashed password to verify against
    
    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
