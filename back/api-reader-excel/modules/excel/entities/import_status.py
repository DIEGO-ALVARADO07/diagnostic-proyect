"""Estados del ciclo de vida de una importación de Excel.

Los valores se guardan tal cual en ``excel_imports.status``; cambiar uno exige
una migración (hay un CHECK en la tabla).
"""

from enum import StrEnum


class ImportStatus(StrEnum):
    PROCESSING = "PROCESSING"
    """Registro creado; el libro se está leyendo y guardando."""
    VALIDATED = "VALIDATED"
    """Datos guardados, aún sin activar (estado transitorio dentro de la transacción)."""
    ACTIVE = "ACTIVE"
    """Instantánea que ven instructores y superadmin."""
    HISTORICAL = "HISTORICAL"
    """Instantánea anterior; solo la consulta el superadmin."""
    FAILED = "FAILED"
    """La importación falló; no tiene datos utilizables."""


# Instantáneas completas e inmutables: se pueden consultar y cachear.
SNAPSHOT_STATUSES = frozenset({ImportStatus.ACTIVE, ImportStatus.HISTORICAL})
# Estados que el superadmin puede desactivar (soft delete).
DEACTIVATABLE_STATUSES = frozenset(
    {ImportStatus.ACTIVE, ImportStatus.HISTORICAL, ImportStatus.FAILED}
)

# Etiqueta que solo aparece en las respuestas cuando ``deleted_at`` tiene valor.
# No es un estado de la base de datos.
DELETED_STATUS_LABEL = "DELETED"

# Único modo de dataset soportado hoy (CHECK ``dataset_mode = 'SNAPSHOT'``).
SNAPSHOT_DATASET_MODE = "SNAPSHOT"

# ``excel_dashboard_state`` tiene una única fila con este id.
DASHBOARD_STATE_ID = 1


def status_sql_check() -> str:
    """Expresión del CHECK de ``excel_imports.status`` derivada del enum."""
    values = ", ".join(f"'{status.value}'" for status in ImportStatus)
    return f"status IN ({values})"
