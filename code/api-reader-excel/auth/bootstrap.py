import os
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from auth.models import Account, AuthBase
from auth.role import Role
from auth.security import hash_password


def main() -> None:
    required = (
        "BOOTSTRAP_SUPERADMIN_USERNAME",
        "BOOTSTRAP_SUPERADMIN_EMAIL",
        "BOOTSTRAP_SUPERADMIN_FULL_NAME",
        "BOOTSTRAP_SUPERADMIN_PASSWORD",
    )
    values = {name: os.environ.get(name, "") for name in required}
    missing = [name for name, value in values.items() if not value.strip()]
    if missing:
        raise SystemExit(f"Faltan variables requeridas: {', '.join(missing)}")
    if len(values["BOOTSTRAP_SUPERADMIN_PASSWORD"]) < 12:
        raise SystemExit("La contraseña inicial debe tener al menos 12 caracteres.")

    username = values["BOOTSTRAP_SUPERADMIN_USERNAME"].strip().casefold()
    email = values["BOOTSTRAP_SUPERADMIN_EMAIL"].strip().casefold()
    full_name = values["BOOTSTRAP_SUPERADMIN_FULL_NAME"].strip()
    if not re.fullmatch(r"[a-z0-9._-]{3,80}", username):
        raise SystemExit(
            "El usuario debe tener 3-80 caracteres alfanuméricos, punto, "
            "guion o guion bajo."
        )
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("El correo electrónico inicial no tiene un formato válido.")
    if len(full_name) > 200:
        raise SystemExit("El nombre inicial no puede superar los 200 caracteres.")

    from core.database import SessionLocal, engine

    AuthBase.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = db.scalar(
            select(Account.id)
            .where(Account.role == Role.SUPERADMIN.value)
            .limit(1)
        )
        if existing is not None:
            raise SystemExit(
                "Ya existe una cuenta superadmin; el aprovisionamiento inicial se canceló."
            )

        account = Account(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hash_password(values["BOOTSTRAP_SUPERADMIN_PASSWORD"]),
            role=Role.SUPERADMIN.value,
        )
        db.add(account)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise SystemExit(
                "No se pudo crear el superadmin: el usuario o correo ya existe."
            ) from None

    print("Cuenta superadmin inicial creada.")


if __name__ == "__main__":
    main()
