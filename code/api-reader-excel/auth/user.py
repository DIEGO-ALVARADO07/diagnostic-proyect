import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from auth.role import Role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: SecretStr = Field(min_length=1)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=200)
    password: SecretStr = Field(min_length=12, max_length=256)
    role: Literal["instructor", "estudiante"]

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("El correo electrónico no tiene un formato válido.")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return value.strip()


class ProfileUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: SecretStr | None = Field(default=None, min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("El correo electrónico no tiene un formato válido.")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class UserUpdate(ProfileUpdate):
    username: str | None = Field(
        default=None, min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$"
    )
    role: Literal["instructor", "estudiante"] | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        return value.strip().casefold() if value is not None else None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: Role
    is_active: bool