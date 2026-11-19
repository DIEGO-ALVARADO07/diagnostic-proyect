from typing import Literal

from pydantic import BaseModel

from modules.security.dtos.responses.users import UserResponse


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse
