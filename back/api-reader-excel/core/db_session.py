"""Sesión de base de datos por petición, compartida por todos los módulos."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    # Importación diferida: core.database crea Settings y el engine al
    # importarse, lo que exige core/.env. Así la app (y los tests) pueden
    # construirse sin credenciales; solo se conectan al atender una petición.
    from core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
