from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from modules.security.database import get_db
from modules.security.dependencies import CurrentAccount, require_permission, require_roles
from modules.security.dtos.requests.users import (
    ProfileUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from modules.security.dtos.responses.users import UserResponse
from modules.security.permission import Permission
from modules.security.role import Role
from modules.security.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission(Permission.READ_USERS))],
)
def list_users(
    account: CurrentAccount,
    db: Session = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[UserResponse]:
    return UserService(db).list_users(account, offset, limit)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
def create_user(
    payload: UserCreateRequest,
    account: CurrentAccount,
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserService(db).create_user(payload, account)


@router.get("/me", response_model=UserResponse)
def read_my_profile(account: CurrentAccount) -> UserResponse:
    return UserService.read_my_profile(account)


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    account: CurrentAccount,
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserService(db).update_my_profile(payload, account)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int, account: CurrentAccount, db: Session = Depends(get_db)
) -> UserResponse:
    return UserService(db).read_user(user_id, account)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    account: CurrentAccount,
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserService(db).update_user(user_id, payload, account)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
def deactivate_user(
    user_id: int,
    account: CurrentAccount,
    db: Session = Depends(get_db),
) -> None:
    UserService(db).deactivate_user(user_id, account)
