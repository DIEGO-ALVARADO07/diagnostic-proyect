import os
import re
from pathlib import Path

from alembic.config import Config

from core.exceptions import ApplicationError
from modules.security.services.bootstrap_service import BootstrapService
from modules.security.services.migration_service import SecurityMigrationService


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

    project_root = Path(__file__).resolve().parents[2]
    migration_config = Config(str(project_root / "alembic.ini"))
    SecurityMigrationService(migration_config, engine).upgrade()
    with SessionLocal() as db:
        try:
            BootstrapService(db).create_superadmin(
                username=username,
                email=email,
                full_name=full_name,
                password=values["BOOTSTRAP_SUPERADMIN_PASSWORD"],
            )
        except ApplicationError as error:
            raise SystemExit(error.detail) from None

    print("Cuenta superadmin inicial creada.")


if __name__ == "__main__":
    main()
