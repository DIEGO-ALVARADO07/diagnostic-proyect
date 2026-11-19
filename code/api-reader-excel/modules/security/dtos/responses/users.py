from pydantic import BaseModel, ConfigDict

from modules.security.entities.role import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: Role
    is_active: bool
