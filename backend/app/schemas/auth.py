from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request schema."""
    factory_id: int
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information in response."""
    id: int
    email: str
    role: str
    permissions: dict | None = None


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class FactoryResponse(BaseModel):
    """Factory information."""
    id: int
    name: str
    slug: str
