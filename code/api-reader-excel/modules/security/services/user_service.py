from http import HTTPStatus
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from modules.security.dtos.requests.users import (
    ProfileUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from modules.security.dtos.responses.users import UserResponse
from modules.security.entities import Account, utcnow
from modules.security.entities.permission import Permission
from modules.security.repositories.account_repository import AccountRepository
from modules.security.repositories.token_repository import TokenRepository
from modules.security.entities.role import Role, has_permission
from modules.security.security import hash_password


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.accounts = AccountRepository(db)
        self.tokens = TokenRepository(db)

    def list_users(
        self, actor: Account, offset: int, limit: int
    ) -> list[UserResponse]:
        role = Role(actor.role)
        if not has_permission(role, Permission.READ_USERS):
            raise ApplicationError(
                HTTPStatus.FORBIDDEN, "No tienes permisos para consultar usuarios."
            )
        excluded_role = Role.SUPERADMIN.value if role == Role.INSTRUCTOR else None
        accounts = self.accounts.list_active(offset, limit, excluded_role)
        return [UserResponse.model_validate(account) for account in accounts]

    def create_user(
        self, payload: UserCreateRequest, actor: Account
    ) -> UserResponse:
        self._require_superadmin(actor)
        account = Account(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password.get_secret_value()),
            role=payload.role,
        )
        self.accounts.add(account)
        return self._commit(account)

    @staticmethod
    def read_my_profile(actor: Account) -> UserResponse:
        return UserResponse.model_validate(actor)

    def update_my_profile(
        self, payload: ProfileUpdateRequest, actor: Account
    ) -> UserResponse:
        changes = self._changes(payload)
        if not changes:
            raise ApplicationError(422, "No se enviaron cambios.")
        self._apply_changes(actor, changes)
        return self._commit(actor)

    def read_user(self, user_id: int, actor: Account) -> UserResponse:
        role = Role(actor.role)
        if role == Role.ESTUDIANTE:
            if user_id != actor.id:
                raise ApplicationError(403, "Solo puedes consultar tu perfil.")
            return UserResponse.model_validate(actor)
        if not has_permission(role, Permission.READ_USERS):
            raise ApplicationError(403, "No tienes permisos para consultar usuarios.")

        target = self._active_user_or_404(user_id)
        if role == Role.INSTRUCTOR and target.role == Role.SUPERADMIN.value:
            raise ApplicationError(404, "Usuario no encontrado.")
        return UserResponse.model_validate(target)

    def update_user(
        self, user_id: int, payload: UserUpdateRequest, actor: Account
    ) -> UserResponse:
        role = Role(actor.role)
        if role == Role.ESTUDIANTE and user_id != actor.id:
            raise ApplicationError(403, "Solo puedes editar tus propios datos.")

        target = actor if user_id == actor.id else self._active_user_or_404(user_id)
        changes = self._changes(payload)
        if not changes:
            raise ApplicationError(422, "No se enviaron cambios.")

        if role == Role.ESTUDIANTE:
            if "username" in changes or "role" in changes:
                raise ApplicationError(403, "No puedes cambiar tu usuario ni tu rol.")
        elif role == Role.INSTRUCTOR:
            if target.role == Role.SUPERADMIN.value:
                raise ApplicationError(403, "No puedes modificar superadmins.")
            if "username" in changes or "role" in changes:
                raise ApplicationError(403, "No puedes cambiar usuarios ni roles.")
            if target.id != actor.id and "password" in changes:
                raise ApplicationError(
                    403, "Solo puedes cambiar tu propia contraseña."
                )

        if role == Role.SUPERADMIN and target.role == Role.SUPERADMIN.value:
            if "role" in changes:
                raise ApplicationError(
                    403, "No se puede cambiar el rol de un superadmin."
                )

        self._apply_changes(target, changes)
        return self._commit(target)

    def deactivate_user(self, user_id: int, actor: Account) -> None:
        self._require_superadmin(actor)
        target = self._active_user_or_404(user_id)
        if target.role == Role.SUPERADMIN.value:
            active_superadmins = self.accounts.count_active_by_role(
                Role.SUPERADMIN.value
            )
            if active_superadmins <= 1:
                raise ApplicationError(
                    409, "No se puede desactivar el último superadmin activo."
                )

        target.is_active = False
        self.tokens.revoke_for_user(target.id)
        self.db.commit()

    @staticmethod
    def _require_superadmin(actor: Account) -> None:
        if Role(actor.role) != Role.SUPERADMIN:
            raise ApplicationError(403, "No tienes permisos para realizar esta acción.")

    def _active_user_or_404(self, user_id: int) -> Account:
        account = self.accounts.get_active_by_id(user_id)
        if account is None:
            raise ApplicationError(404, "Usuario no encontrado.")
        return account

    @staticmethod
    def _changes(
        payload: ProfileUpdateRequest | UserUpdateRequest,
    ) -> dict[str, object]:
        return {
            key: value
            for key, value in payload.model_dump(exclude_unset=True).items()
            if value is not None
        }

    @staticmethod
    def _apply_changes(account: Account, changes: dict[str, object]) -> None:
        password = changes.pop("password", None)
        if isinstance(password, SecretStr):
            changes["password_hash"] = hash_password(password.get_secret_value())
        for field, value in changes.items():
            setattr(account, field, value)

    def _commit(self, account: Account) -> UserResponse:
        account.updated_at = utcnow()
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "El nombre de usuario o correo ya está en uso.",
            ) from None
        self.db.refresh(account)
        return UserResponse.model_validate(account)
