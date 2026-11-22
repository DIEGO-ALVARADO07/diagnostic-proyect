"""Engine y fábrica de sesiones de MySQL.

Importar este módulo carga la configuración (core/.env). Las rutas no lo
importan directamente: usan ``core.db_session.DbSession``.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
