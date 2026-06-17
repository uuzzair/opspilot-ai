"""Authentication API schemas."""
from pydantic import BaseModel, Field, field_validator


class UserRegister(BaseModel):
    """Request body for user registration."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize and lightly validate an email address."""
        email = value.strip().lower()
        if "@" not in email:
            raise ValueError("Invalid email address")
        return email


class UserLogin(BaseModel):
    """Request body for user login."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email for lookup."""
        return value.strip().lower()


class TokenRead(BaseModel):
    """Access token response."""

    access_token: str
    token_type: str = "bearer"
