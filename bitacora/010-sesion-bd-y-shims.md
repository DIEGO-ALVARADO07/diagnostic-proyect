# 010 · Sesión de BD en `core` y eliminación de archivos de compatibilidad

- **Fase:** 3
- **Fecha:** 2026-11-22

## Problema

- Había **dos `get_db`**: el de `core/database.py` no lo usaba nadie, y su `Base = declarative_base()` tampoco. El que sí se usaba vivía en `modules/security/database.py`, así que el módulo `excel` dependía de `security` solo para obtener una sesión.
- Las rutas mezclaban dos estilos: `db: Session = Depends(get_db)` y `db: DbSession`.
- Seguían cinco archivos de compatibilidad ("fachadas") que solo reexportaban otros: `modules/excel/service.py`, `modules/security/models.py`, `role.py`, `permission.py` y `user.py`. `users/routes.py` y los tests todavía importaban desde ellos.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/core/db_session.py` | **Nuevo.** `get_db()` con importación diferida de `SessionLocal`, y `DbSession = Annotated[Session, Depends(get_db)]`. |
| `back/api-reader-excel/core/database.py` | Solo quedan `engine` y `SessionLocal`. Se eliminan `Base` y `get_db`, que no se usaban. Docstring nuevo. |
| `back/api-reader-excel/modules/security/database.py` | **Eliminado.** Lo reemplaza `core/db_session.py`. |
| `modules/excel/service.py`, `modules/security/models.py`, `role.py`, `permission.py`, `user.py` | **Eliminados.** |
| `modules/security/dependencies.py`, `routes.py`, `users/routes.py`, `modules/excel/routes.py` | Todas las rutas usan `db: DbSession` desde `core.db_session` e importan desde `entities` y `dtos`. |
| `tests/test_auth.py`, `test_excel.py`, `test_security_migrations.py` | Importan desde las rutas reales. `test_excel.py` define localmente el `read_first_sheet` que antes daba el archivo de compatibilidad, para no perder las 4 pruebas. |
| `back/api-reader-excel/IMPLEMENTATION.md` | Se actualizan las menciones a las fachadas y a `modules/security/database.py`. |

## Por qué la importación diferida

`core/database.py` crea `Settings` y el engine al importarse, y eso exige `core/.env` (y `APP_MASTER_KEY` si va cifrado). Al importarlo **dentro** de `get_db`:

- la app y las pruebas se construyen sin credenciales;
- solo falla la primera petición que realmente necesita la base de datos.

Se mantiene el comportamiento anterior, ahora en un solo lugar.

## Comprobación

`pyflakes` sobre `modules`, `core`, `app`, `api` y `tests` no encuentra imports sin usar ni referencias rotas. Una búsqueda de `security.database`, `modules.excel.service` y `HTTPException` no da resultados.
