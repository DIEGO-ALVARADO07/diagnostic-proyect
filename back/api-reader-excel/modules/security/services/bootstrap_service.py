from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from modules.security.entities import Account
from modules.security.repositories.account_repository import AccountRepository
from modules.security.entities.role import Role
from modules.security.security import hash_password


class BootstrapService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = AccountRepository(db)

    def create_superadmin(
        self, username: str, email: str, full_name: str, password: str
    ) -> None:
        if self.accounts.exists_with_role(Role.SUPERADMIN.value):
            raise ApplicationError(
                409,
                "Ya existe una cuenta superadmin; el aprovisionamiento inicial se canceló.",
            )

        self.accounts.add(
            Account(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=Role.SUPERADMIN.value,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ApplicationError(
                409,
                "No se pudo crear el superadmin: el usuario o correo ya existe.",
            ) from None
