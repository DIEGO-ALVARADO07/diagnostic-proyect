from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.database import get_db
from auth.dependencies import CurrentAccount, require_permission, require_roles
from auth.models import AccessToken, Account, utcnow
from auth.permission import Permission
from auth.role import Role, has_permission
from auth.security import hash_password
from auth.user import ProfileUpdate, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
DbSession = Annotated[Session, Depends(get_db)]


def _active_user_or_404(db: Session, user_id: int) -> Account:
    account = db.scalar(
        select(Account).where(Account.id == user_id, Account.is_active.is_(True))
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return account


def _commit_update(db: Session, account: Account) -> Account:
    account.updated_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario o correo ya está en uso.",
        ) from None
    db.refresh(account)
    return account


@router.get(
    "",
    response_model=list[UserRead],
    dependencies=[Depends(require_permission(Permission.READ_USERS))],
)
def list_users(
    account: CurrentAccount,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Account]:
    statement = select(Account).where(Account.is_active.is_(True))
    if Role(account.role) == Role.INSTRUCTOR:
        statement = statement.where(Account.role != Role.SUPERADMIN.value)
    return list(
        db.scalars(
            statement.order_by(Account.id).offset(offset).limit(limit)
        )
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
def create_user(payload: UserCreate, db: DbSession) -> Account:
    account = Account(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=payload.role,
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario o correo ya está en uso.",
        ) from None
    db.refresh(account)
    return account


@router.get("/me", response_model=UserRead)
def read_my_profile(account: CurrentAccount) -> Account:
    return account


@router.patch("/me", response_model=UserRead)
def update_my_profile(
    payload: ProfileUpdate, account: CurrentAccount, db: DbSession
) -> Account:
    changes = payload.model_dump(exclude_unset=True)
    changes = {key: value for key, value in changes.items() if value is not None}
    if not changes:
        raise HTTPException(status_code=422, detail="No se enviaron cambios.")
    if "password" in changes:
        changes["password_hash"] = hash_password(
            changes.pop("password").get_secret_value()
        )
    for field, value in changes.items():
        setattr(account, field, value)
    return _commit_update(db, account)


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, account: CurrentAccount, db: DbSession) -> Account:
    role = Role(account.role)
    if role == Role.ESTUDIANTE:
        if user_id != account.id:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tu perfil.")
        return account
    if not has_permission(role, Permission.READ_USERS):
        raise HTTPException(
            status_code=403, detail="No tienes permisos para consultar usuarios."
        )
    target = _active_user_or_404(db, user_id)
    if role == Role.INSTRUCTOR and target.role == Role.SUPERADMIN.value:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return target


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    account: CurrentAccount,
    db: DbSession,
) -> Account:
    role = Role(account.role)
    if role == Role.ESTUDIANTE and user_id != account.id:
        raise HTTPException(status_code=403, detail="Solo puedes editar tus propios datos.")

    target = account if user_id == account.id else _active_user_or_404(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    changes = {key: value for key, value in changes.items() if value is not None}
    if not changes:
        raise HTTPException(status_code=422, detail="No se enviaron cambios.")

    if role == Role.ESTUDIANTE:
        if "username" in changes or "role" in changes:
            raise HTTPException(
                status_code=403, detail="No puedes cambiar tu usuario ni tu rol."
            )
    elif role == Role.INSTRUCTOR:
        if target.role == Role.SUPERADMIN.value:
            raise HTTPException(status_code=403, detail="No puedes modificar superadmins.")
        if "username" in changes or "role" in changes:
            raise HTTPException(
                status_code=403, detail="No puedes cambiar usuarios ni roles."
            )
        if target.id != account.id and "password" in changes:
            raise HTTPException(
                status_code=403,
                detail="Solo puedes cambiar tu propia contraseña.",
            )

    if role == Role.SUPERADMIN and target.role == Role.SUPERADMIN.value:
        if "role" in changes:
            raise HTTPException(
                status_code=403, detail="No se puede cambiar el rol de un superadmin."
            )

    if "password" in changes:
        changes["password_hash"] = hash_password(
            changes.pop("password").get_secret_value()
        )
    for field, value in changes.items():
        setattr(target, field, value)
    return _commit_update(db, target)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
def deactivate_user(user_id: int, db: DbSession) -> None:
    target = _active_user_or_404(db, user_id)
    if target.role == Role.SUPERADMIN.value:
        active_superadmins = db.scalar(
            select(func.count())
            .select_from(Account)
            .where(
                Account.role == Role.SUPERADMIN.value,
                Account.is_active.is_(True),
            )
        )
        if active_superadmins is not None and active_superadmins <= 1:
            raise HTTPException(
                status_code=409,
                detail="No se puede desactivar el último superadmin activo.",
            )

    target.is_active = False
    db.query(AccessToken).filter(AccessToken.user_id == target.id).update(
        {AccessToken.revoked: True}, synchronize_session=False
    )
    db.commit()
