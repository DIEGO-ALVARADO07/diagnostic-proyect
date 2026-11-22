"""Base declarativa compartida por todos los modelos ORM de la aplicación.

Todos los módulos (security, excel, …) registran sus tablas en esta misma
metadata, que es la que versiona Alembic en ``migrations/``.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Fecha y hora UTC sin zona horaria (las columnas DateTime son naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
