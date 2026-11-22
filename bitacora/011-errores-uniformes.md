# 011 · Errores uniformes: `ApplicationError` y `HTTPStatus`

- **Fase:** 3
- **Fecha:** 2026-11-22

## Problema

- Las dependencias de seguridad (`require_roles`, `require_permission`, `get_current_token`, `get_current_account`) lanzaban `fastapi.HTTPException`. Los servicios lanzaban `core.exceptions.ApplicationError`. Eran dos mecanismos para lo mismo.
- Los servicios de seguridad usaban números sueltos (`403`, `404`, `422`, `409`, `401`), mientras que los de Excel usaban `HTTPStatus.X`.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/modules/security/dependencies.py` | Reescrito: lanza `ApplicationError` mediante `_unauthorized()` (401 con `WWW-Authenticate: Bearer`) y `_forbidden()` (403). Imports ordenados. |
| `modules/security/services/user_service.py`, `auth_service.py`, `bootstrap_service.py` | 17 códigos numéricos pasan a `HTTPStatus.*`. Se elimina un import sin usar (`Account` en `auth_service.py`). |
| `tests/test_auth.py`, `tests/test_dashboard.py` | Los guardas de rol ahora esperan `ApplicationError`; el código 403 no cambia. |
| `back/api-reader-excel/tests/test_error_handling.py` | **Nuevo.** 2 pruebas: el handler de `ApplicationError` mantiene el contrato (`401`, `WWW-Authenticate: Bearer`, cuerpo `{"detail": "…"}`) y conserva el `detail` estructurado (`{"message", "available_sheets"}`). |

## Por qué no cambia nada para el frontend

El handler de `ApplicationError` (`app/__init__.py`) devuelve `{"detail": …}` con el mismo código y las mismas cabeceras que `HTTPException`. Lo verifiqué contra Uvicorn real: `GET /users/me` y `GET /excel/dashboard/active` sin token responden **401** con `WWW-Authenticate: Bearer`.

## Nota

En Python 3.13 o superior, `HTTPStatus(422).name` es `UNPROCESSABLE_CONTENT`. Se usa el alias `UNPROCESSABLE_ENTITY`, que es el que ya usaba el resto del código.
