"""Compatibility exports for the original security DTO import path."""

from modules.security.dtos.requests.auth import LoginRequest
from modules.security.dtos.requests.users import (
    ProfileUpdateRequest as ProfileUpdate,
    UserCreateRequest as UserCreate,
    UserUpdateRequest as UserUpdate,
)
from modules.security.dtos.responses.users import UserResponse as UserRead

__all__ = [
    "LoginRequest",
    "ProfileUpdate",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
