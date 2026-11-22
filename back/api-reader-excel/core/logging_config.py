"""Configuración centralizada de logging de la aplicación.

Se resuelve sin instanciar ``core.config.Settings`` para que la app pueda
crearse (por ejemplo, en los tests) sin credenciales de base de datos.
"""

import logging
import os

from dotenv import dotenv_values

from core.paths import ENV_FILE

DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def resolve_log_level() -> str:
    """Prioridad: variable de entorno LOG_LEVEL > core/.env > INFO."""
    level = os.getenv("LOG_LEVEL")
    if not level and ENV_FILE.is_file():
        level = dotenv_values(ENV_FILE).get("LOG_LEVEL")
    level = (level or DEFAULT_LOG_LEVEL).strip().upper()
    if level not in logging.getLevelNamesMapping():
        return DEFAULT_LOG_LEVEL
    return level


def configure_logging(level: str | None = None) -> None:
    """Configura el logger raíz una sola vez.

    Los loggers de Uvicorn tienen sus propios handlers y no se duplican.
    Los loggers de la app (``modules.*``) se propagan al raíz y quedan visibles.
    """
    logging.basicConfig(
        level=level or resolve_log_level(),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )
