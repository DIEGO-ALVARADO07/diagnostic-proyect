# 013 · `Base` del ORM y migraciones fuera del módulo `security`

- **Fase:** 4 (estructura)
- **Fecha:** 2026-11-22

## Problema

- La base declarativa `AuthBase` y `utcnow()` vivían en `modules/security/entities/base.py`. Las 7 tablas académicas del módulo `excel` heredaban de ella, así que `excel` dependía de `security` solo para declarar sus tablas.
- Las migraciones de **todo** el esquema, incluidas las del dashboard, estaban en `modules/security/migrations`. El servicio que las aplica se llamaba `SecurityMigrationService` aunque migra todas las tablas.
- Había un paquete vacío, `modules/excel/migrations/`.

## Qué se cambió

| Antes | Ahora |
|---|---|
| `modules/security/entities/base.py` (`AuthBase`, `utcnow`) | `core/orm.py` (`Base`, `utcnow`) |
| `modules/security/migrations/` (env, versiones, `__main__`) | `migrations/` en la raíz del backend |
| `modules/security/services/migration_service.py` (`SecurityMigrationService`) | `migrations/runner.py` (`DatabaseMigrationService`) |
| `python -m modules.security.migrations` | `python -m migrations` (`.\tasks.ps1 migrate` ya lo usa) |
| `modules/excel/migrations/__init__.py` | Eliminado (estaba vacío) |

Archivos actualizados: los modelos de `security` y `excel`, `alembic.ini`, `migrations/env.py`, `migrations/__main__.py`, `modules/security/bootstrap.py`, `tasks.ps1`, los tests, `scripts/bench_dashboard.py` e `IMPLEMENTATION.md`. Los archivos se movieron con `git mv`, así que conservan su historial.

## Por qué es seguro con bases existentes

- Alembic identifica cada migración por su **revisión** (`0001_security_tables`, `0002_academic_dashboard`, `0003_soft_delete_excel_imports`), no por la carpeta. La tabla `alembic_version` de tus bases sigue siendo válida. Lo comprobé: Alembic encuentra las 3 revisiones y la cabeza es `0003`.
- El nombre de la clase base no aparece en la base de datos. Las tablas y columnas no cambian.

## Verificación

- 45 pruebas OK. `pyflakes` sin avisos.
- La foto de regresión con `CORHUILA.xlsm` es **idéntica** antes y después (ver entrada 016).
