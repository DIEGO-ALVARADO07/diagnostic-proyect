from datetime import timedelta

from core.exceptions import ApplicationError
from modules.security.dtos.requests.auth import LoginRequest
from modules.security.dtos.responses.auth import LoginResponse
from modules.security.dtos.responses.users import UserResponse
from modules.security.entities import AccessToken, Account, utcnow
from modules.security.repositories.account_repository import AccountRepository
from modules.security.repositories.token_repository import TokenRepository
from modules.security.security import (
    create_access_token,
    hash_access_token,
    verify_password,
)
from sqlalchemy.orm import Session

ACCESS_TOKEN_TTL_MINUTES = 480


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.tokens = TokenRepository(db)

    def login(self, payload: LoginRequest) -> LoginResponse:
        username = payload.username.strip().casefold()
        account = self.accounts.get_by_username(username)
        if (
            account is None
            or not account.is_active
            or not verify_password(
                payload.password.get_secret_value(),
                account.password_hash if account is not None else "",
            )
        ):
            raise ApplicationError(
                401,
                "Usuario o contraseña incorrectos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        raw_token = create_access_token()
        self.tokens.add(
            AccessToken(
                user_id=account.id,
                token_hash=hash_access_token(raw_token),
                expires_at=utcnow() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
            )
        )
        self.db.commit()
        return LoginResponse(
            access_token=raw_token,
            expires_in=ACCESS_TOKEN_TTL_MINUTES * 60,
            user=UserResponse.model_validate(account),
        )

    def logout(self, token: AccessToken) -> None:
        token.revoked = True
        self.db.commit()
