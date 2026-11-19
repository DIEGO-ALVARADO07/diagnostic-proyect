from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from modules.security.entities.access_token import AccessToken


class TokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active(self, token_hash: str, now: datetime) -> AccessToken | None:
        return self.db.scalar(
            select(AccessToken).where(
                AccessToken.token_hash == token_hash,
                AccessToken.revoked.is_(False),
                AccessToken.expires_at > now,
            )
        )

    def add(self, token: AccessToken) -> None:
        self.db.add(token)

    def revoke_for_user(self, user_id: int) -> None:
        self.db.execute(
            update(AccessToken)
            .where(AccessToken.user_id == user_id)
            .values(revoked=True)
        )
