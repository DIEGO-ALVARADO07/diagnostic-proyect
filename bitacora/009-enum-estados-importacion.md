# 009 · Enum `ImportStatus` y constantes del dashboard

- **Fase:** 3 (limpieza interna; la API responde igual)
- **Fecha:** 2026-11-22

## Problema

Los estados de importación (`"PROCESSING"`, `"VALIDATED"`, `"ACTIVE"`, `"HISTORICAL"`, `"FAILED"`) y la etiqueta `"DELETED"` estaban escritos como texto en unos 20 lugares, repartidos entre el modelo ORM, el repositorio y el servicio. Además:

- el id de la fila única `excel_dashboard_state` (`1`) estaba repetido 4 veces;
- el bloqueo `SELECT … FOR UPDATE` de esa fila estaba duplicado en el servicio;
- `list_imports` y `list_admin_imports` repetían el mismo mapeo de 18 líneas.

Con texto libre, una errata (`"ACTIVO"`) no da error: simplemente no coincide nunca.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/modules/excel/entities/import_status.py` | **Nuevo.** `ImportStatus(StrEnum)` con un docstring por estado, más estas constantes: `SNAPSHOT_STATUSES` (ACTIVE e HISTORICAL), `DEACTIVATABLE_STATUSES` (además FAILED), `DELETED_STATUS_LABEL`, `SNAPSHOT_DATASET_MODE` y `DASHBOARD_STATE_ID`. También `status_sql_check()`, que genera el CHECK de la tabla a partir del enum. |
| `back/api-reader-excel/modules/excel/entities/academic.py` | El CHECK y los valores por defecto de `ExcelImport` salen del enum y las constantes. |
| `back/api-reader-excel/modules/excel/repositories/dashboard_persistence_repository.py` | Usa las constantes. Nuevo método `lock_dashboard_state(db)`. |
| `back/api-reader-excel/modules/excel/services/dashboard_service.py` | Sin texto literal de estados. El bloqueo pasa a `persistence.lock_dashboard_state`. Nuevo `_import_list_response()`, que comparten los dos listados. Se elimina `_CACHEABLE_STATUSES` (fase 2) en favor de `SNAPSHOT_STATUSES`. |

## Decisiones

- **`StrEnum`** (Python 3.11 o superior): sus miembros *son* `str`. Siguen funcionando las comparaciones con lo que devuelve la base de datos (`"ACTIVE" == ImportStatus.ACTIVE`), la columna `String(20)` y los DTOs con `status: str`. **No hace falta migración.**
- `status_sql_check()` genera exactamente el mismo texto que la migración `0002` (`status IN ('PROCESSING', 'VALIDATED', 'ACTIVE', 'HISTORICAL', 'FAILED')`). Lo verifiqué con una aserción.
- `DELETED` **no** es un miembro del enum, porque no existe en la base de datos: es solo una etiqueta de respuesta cuando `deleted_at` tiene valor. Por eso es una constante aparte.
