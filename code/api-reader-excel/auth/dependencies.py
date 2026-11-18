from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.database import get_db
from auth.models import AccessToken, Account
from auth.permission import Permission
from auth.role import Role, has_permission
from auth.security import hash_access_token

_bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de acceso inválidas o vencidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_token(
    credentials: BearerCredentials, db: DbSession
) -> AccessToken:
    if credentials is None:
        raise _unauthorized()

    token = db.scalar(
        select(AccessToken).where(
            AccessToken.token_hash == hash_access_token(credentials.credentials),
            AccessToken.revoked.is_(False),
            AccessToken.expires_at
            > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    if token is None:
        raise _unauthorized()
    return token


CurrentToken = Annotated[AccessToken, Depends(get_current_token)]


def get_current_account(token: CurrentToken, db: DbSession) -> Account:
    account = db.get(Account, token.user_id)
    if account is None or not account.is_active:
        raise _unauthorized()
    try:
        Role(account.role)
    except ValueError:
        raise _unauthorized() from None
    return account


CurrentAccount = Annotated[Account, Depends(get_current_account)]


def require_roles(*allowed_roles: Role) -> Callable[..., Account]:
    def dependency(account: CurrentAccount) -> Account:
        if Role(account.role) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return account

    return dependency


def require_permission(permission: Permission) -> Callable[..., Account]:
    def dependency(account: CurrentAccount) -> Account:
        if not has_permission(Role(account.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return account

    return dependency
