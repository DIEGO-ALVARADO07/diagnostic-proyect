from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.security.entities.account import Account


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> Account | None:
        return self.db.scalar(select(Account).where(Account.username == username))

    def get_active_by_id(self, user_id: int) -> Account | None:
        return self.db.scalar(
            select(Account).where(Account.id == user_id, Account.is_active.is_(True))
        )

    def list_active(
        self, offset: int, limit: int, excluded_role: str | None = None
    ) -> list[Account]:
        statement = select(Account).where(Account.is_active.is_(True))
        if excluded_role is not None:
            statement = statement.where(Account.role != excluded_role)
        return list(
            self.db.scalars(statement.order_by(Account.id).offset(offset).limit(limit))
        )

    def count_active_by_role(self, role: str) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Account)
                .where(Account.role == role, Account.is_active.is_(True))
            )
            or 0
        )

    def exists_with_role(self, role: str) -> bool:
        return (
            self.db.scalar(select(Account.id).where(Account.role == role).limit(1))
            is not None
        )

    def add(self, account: Account) -> None:
        self.db.add(account)
