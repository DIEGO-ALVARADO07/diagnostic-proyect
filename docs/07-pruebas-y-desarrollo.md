# Pruebas y desarrollo

## Pruebas automatizadas

Desde `back/api-reader-excel`:

```powershell
.\tasks.ps1 test
```

Ejecuta `python -m unittest discover -s tests` con el Python del `venv` y `LOG_LEVEL=WARNING` (para que los logs no se mezclen con el reporte). **58 pruebas**, todas en SQLite en memoria: no necesitan `core/.env` ni MySQL.

| Archivo | Cubre |
|---|---|
| `tests/test_auth.py` | Hash de contraseñas, permisos por rol, login con hash del token, edición de perfiles y restricciones. |
| `tests/test_config.py` | Contrato de configuración de la base de datos. |
| `tests/test_excel.py` | Lectura de la primera hoja o de una hoja elegida y errores de Excel. |
| `tests/test_dashboard.py` | Lectura de `BD GEN`/`TD PROGRAMAS` (incluido un libro que empieza en la fila `AÑO`), importación idempotente, métricas, historial, activación, desactivación lógica y permisos. |
| `tests/test_dashboard_cache.py` | Caché LRU de datasets y su relación con la desactivación (incluido el caso de varios procesos). |
| `tests/test_dashboard_rules.py` | Reglas de datos: nombre de programa, unificación con alias, semestres y reporte de calidad. |
| `tests/test_error_handling.py` | Contrato de errores (`401` con `WWW-Authenticate`, `{"detail": ...}`). |
| `tests/test_security_migrations.py` | Cadena de migraciones `0001`–`0004` frente a los modelos, reversión, fusión de programas de `0004` y bases antiguas sin historial. |

La prueba de migraciones sobre SQLite no sustituye validar la migración en el MySQL de destino (con copia de seguridad).

Para ejecutar un solo archivo:

```powershell
$env:PYTHONPATH = "."; .\venv\Scripts\python.exe -m unittest tests.test_dashboard_rules -v
```

## Medir rendimiento

`scripts/bench_dashboard.py` genera un libro sintético, lo importa en SQLite y mide las consultas del dashboard (primera llamada y siguientes, que salen de la caché):

```powershell
$env:PYTHONPATH = "."; .\venv\Scripts\python.exe scripts\bench_dashboard.py 20000
```

Referencia (20.000 filas, 22/11/2026): overview ~197 ms, overview filtrado ~89 ms, programa ~134 ms, estudiante ~7 ms. Sin la caché (antes de la fase 2) cada consulta tardaba ~1 s.

## Revisión estática

Para detectar imports sin usar o nombres rotos se usó `pyflakes` (instalado localmente en el `venv`; aún no está en `requirements.txt`, ver fase 6 en el [estado del proyecto](10-estado-y-continuidad.md)):

```powershell
.\venv\Scripts\python.exe -m pyflakes modules core app api tests migrations scripts
```

Validación del frontend desde la raíz del repositorio:

```powershell
php -l front\index.php
php -l front\partials\imports\screen.php
php -l front\partials\profile\screen.php
```

## Ejecutar para desarrollo

```powershell
.\tasks.ps1 run
```

Arranca Uvicorn con recarga automática; la documentación OpenAPI queda en `http://127.0.0.1:8000/docs`. Para ver más detalle en los logs, define `LOG_LEVEL=DEBUG` en `core/.env` o en la terminal.

## Dónde está cada cosa

```text
back/api-reader-excel/
├── app/            crea la app FastAPI y configura logging y errores
├── api/            ensambla los routers
├── core/           config, engine, sesión por petición, Base ORM, errores, logging
├── migrations/     Alembic (env, runner y versiones 0001–0004)
├── modules/
│   ├── security/   autenticación, usuarios, roles y permisos
│   └── excel/      lectura de Excel y dashboard académico
├── scripts/        utilidades: backup_db (copias), reset_db (vaciar la base), benchmark
├── tests/
└── tasks.ps1       install / migrate / bootstrap / run / test / backup / backup-daily / schedule-backup / reset
```

## Guía para agregar una funcionalidad

1. Crear o extender el módulo bajo `modules/<nombre>/`.
2. Definir los DTOs request/response necesarios, sin usar entidades ORM como contrato del frontend.
3. Implementar las reglas en `services/` (un servicio por caso de uso; funciones puras cuando no hay estado).
4. Implementar acceso a datos o adaptadores en `repositories/`.
5. Mantener las rutas delgadas, recibir la sesión con `db: DbSession` (`core/db_session.py`) y registrar el router en `api/__init__.py`.
6. Lanzar errores de negocio con `core.exceptions.ApplicationError` y un `HTTPStatus`.
7. Si se agrega persistencia: modelos sobre `core.orm.Base` y una migración nueva en `migrations/versions/`; nunca crear tablas al iniciar la API. Añadir la migración a `test_security_migrations.py`.
8. Añadir pruebas y registrar el cambio en la [bitácora](bitacora/README.md).

## Limitaciones conocidas

- `POST /excel/read` devuelve la hoja completa como JSON: un archivo cercano a 30 MB puede producir una respuesta muy grande.
- La caché del dashboard vive en memoria de cada proceso: se vacía al reiniciar y la primera consulta vuelve a cargar desde MySQL.
- Python 3.15.2 es la versión del entorno probado; no hay un rango oficial de versiones.
