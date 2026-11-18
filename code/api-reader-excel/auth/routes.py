from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.database import get_db
from auth.dependencies import CurrentToken
from auth.models import AccessToken, Account, utcnow
from auth.security import (
    create_access_token,
    hash_access_token,
    verify_password,
)
from auth.user import LoginRequest, UserRead

ACCESS_TOKEN_TTL_MINUTES = 480

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip().casefold()
    account = db.scalar(select(Account).where(Account.username == username))
    if (
        account is None
        or not account.is_active
        or not verify_password(
            payload.password.get_secret_value(),
            account.password_hash if account is not None else "",
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = create_access_token()
    db.add(
        AccessToken(
            user_id=account.id,
            token_hash=hash_access_token(raw_token),
            expires_at=utcnow() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        )
    )
    db.commit()
    return LoginResponse(
        access_token=raw_token,
        expires_in=ACCESS_TOKEN_TTL_MINUTES * 60,
        user=UserRead.model_validate(account),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: CurrentToken, db: Session = Depends(get_db)) -> Response:
    token.revoked = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
