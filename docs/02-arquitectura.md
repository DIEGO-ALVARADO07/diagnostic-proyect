# Arquitectura y flujo de datos

## Estilo arquitectónico

La API usa un **monolito modular**. Seguridad y Excel comparten proceso, configuración y conexión a base de datos, pero cada módulo encapsula sus rutas y casos de uso. No hay comunicación de red entre módulos ni despliegues independientes.

```text
Uvicorn
└── app.create_app()
    └── api (ensambla los routers)
        ├── modules.security
        └── modules.excel
```

## Capas por módulo

| Capa | Responsabilidad |
|---|---|
| `routes.py` / `users/routes.py` | Adaptar HTTP, recibir entradas, invocar servicios y declarar respuestas. |
| `dtos/requests` | Validar y normalizar datos de entrada; limitar valores admitidos. |
| `dtos/responses` | Definir explícitamente el contrato que recibe el frontend. |
| `services` | Aplicar reglas de negocio y coordinar el caso de uso. |
| `repositories` | Consultar o persistir datos, o adaptar la lectura del libro Excel. |
| `entities` | Representar entidades persistentes o del dominio del módulo. |
| `entities` (dominio) | Tipos sin dependencias de framework: `Role`, `Permission`, `ImportStatus`, `Competency`, registros y dataset del dashboard. |

Las migraciones de todos los módulos están en `back/api-reader-excel/migrations/`. Los antiguos módulos de compatibilidad (`models.py`, `role.py`, `permission.py`, `user.py`, `excel/service.py`) se eliminaron: se importa siempre desde `entities/` o `dtos/`.

## Componentes compartidos

- `app/`: construye la aplicación FastAPI, configura el logging y convierte los errores esperados `ApplicationError` en respuestas HTTP `{"detail": ...}`. Las dependencias de seguridad también usan `ApplicationError` (`401` con `WWW-Authenticate: Bearer`, `403`).
- `api/`: registra los routers disponibles.
- `core/config.py`: carga `DB_*` desde `core/.env` y descifra usuario/contraseña cuando están cifrados con Fernet.
- `core/database.py`: crea el engine SQLAlchemy y la fábrica de sesiones.
- `core/db_session.py`: `get_db` y el tipo `DbSession`, que todas las rutas usan para recibir una sesión por petición. Importa la configuración de forma diferida, así la app y las pruebas se construyen sin credenciales.
- `core/orm.py`: base declarativa `Base` compartida por todos los modelos y `utcnow()`.
- `core/logging_config.py`: formato y nivel de logs (`LOG_LEVEL`).
- `migrations/`: Alembic (`env.py`, `runner.py` con `DatabaseMigrationService` y las revisiones `0001`–`0004`).

### Servicios del dashboard (`modules/excel/services`)

| Archivo | Responsabilidad |
|---|---|
| `dashboard_service.py` | Punto de entrada que usan las rutas: compone los servicios y comparte la caché. |
| `dashboard_import_service.py` | Importar, activar, listar y desactivar importaciones. |
| `dashboard_query_service.py` | Overview, programa, estudiante e importación activa (solo lectura). |
| `dashboard_dataset_loader.py` | Arma el dataset inmutable de una importación desde MySQL o desde la caché. |
| `dashboard_cache.py` | Caché LRU en memoria (3 importaciones) de datasets. |
| `dashboard_filters.py`, `dashboard_mappers.py` | Filtros y conversión a DTOs de respuesta. |
| `dashboard_audit.py` | Comparación de `TD PROGRAMAS` con lo calculado desde `BD GEN`. |
| `dashboard_metrics.py` | Promedios, desviaciones y distribución por niveles. |
| `dashboard_processor.py`, `dashboard_normalizer.py` | Interpretación y normalización de las filas del Excel. |
| `program_catalog.py`, `dashboard_data_quality.py` | Regla de identidad/nombre de programas y reporte de calidad de datos. |

Las competencias (clave, encabezado en el Excel, columnas en la base y umbrales de nivel) se definen una sola vez en `modules/excel/entities/competency.py`.

## Flujo de autenticación

1. `POST /auth/login` recibe `LoginRequest`.
2. `AuthService` normaliza el usuario y busca la cuenta por medio de `AccountRepository`.
3. La contraseña se verifica contra su hash PBKDF2-HMAC-SHA256.
4. Si es válida, el servicio genera un token opaco. `TokenRepository` guarda solamente su hash y vencimiento.
5. Se responde con `LoginResponse` y `UserResponse`; la respuesta no incluye el hash de contraseña.
6. En solicitudes protegidas, `CurrentAccount` extrae el Bearer token, compara su hash, comprueba revocación y vencimiento, y carga la cuenta activa. Las dependencias de permisos verifican las acciones permitidas.

## Flujo de usuarios

```text
HTTP request
  → DTO request
  → route
  → UserService (reglas/roles)
  → AccountRepository / TokenRepository
  → SQLAlchemy entities
  → DTO response
  → HTTP response
```

El servicio aplica los límites de rol y de cuenta propia, cifra las contraseñas mediante hash antes de persistir, confirma transacciones y convierte conflictos de unicidad en HTTP `409`.

## Flujo de Excel

`POST /excel/read` y `POST /excel/dashboard/import` tienen propósitos diferentes:

- **Lectura/previsualización:** `/excel/read` abre la hoja seleccionada y devuelve sus filas como JSON. No guarda el archivo ni los datos.
- **Dashboard persistente:** `/excel/dashboard/import` lee únicamente `BD GEN` y `TD PROGRAMAS`, normaliza las filas, persiste resultados y referencia dinámica, y activa una versión del conjunto de datos.

Ambos validan el rol y tamaño máximo de 30 MB y ejecutan el parseo fuera del event loop. Ninguno procesa macros o guarda el archivo binario.

## Flujo de importación persistente

```text
Instructor/superadmin
  → POST /excel/dashboard/import (Bearer + archivo)
  → validación de archivo y hojas requeridas
  → SHA-256 e idempotencia
  → lectura de BD GEN + referencia visible de TD PROGRAMAS
  → validación y normalización por fila
  → transacción: estudiantes/programas/resultados/referencias
  → cambio atómico de snapshot activo
  → respuesta con filtros, auditoría, métricas y página 1 (máximo 50 programas)
```

1. Se registra una importación `PROCESSING` con hash y datos de auditoría. Un hash ya conocido no crea una segunda carga. Si su importación fue desactivada, la API responde `409`; no la restaura automáticamente.
2. `DashboardWorkbookRepository` valida encabezados y extrae las dos hojas requeridas; `DashboardProcessor` convierte cada intento de origen en un registro listo para persistir.
3. La transacción inserta resultados con unicidad `(import_id, source_row_number)`, la referencia visible de `TD PROGRAMAS` y las dimensiones reutilizables de estudiante/programa.
4. `excel_dashboard_state` es una fila de coordinación bloqueada al activar: el snapshot anterior pasa a `HISTORICAL` y el nuevo a `ACTIVE` en el mismo commit. Si falla el procesamiento, el lote de resultados se revierte y la importación queda `FAILED`.
5. Las consultas validan en cada petición, contra MySQL, que la importación sea visible (estado, `deleted_at` y rol). Los datos de la importación salen de una caché en memoria del proceso, porque una importación activa o histórica no cambia; la primera consulta tras arrancar la carga desde MySQL. Como la visibilidad se comprueba siempre en la base, varios procesos con cachés independientes siguen siendo correctos.

El superadmin puede desactivar snapshots `ACTIVE`, `HISTORICAL` o `FAILED` mediante una marca `deleted_at`; no se borran sus filas. Al desactivar el activo, se limpia `active_import_id` y el dashboard queda sin snapshot activo hasta la siguiente importación. Las consultas normales ocultan los desactivados y el endpoint administrativo los presenta como `DELETED`. El instructor solo consulta el snapshot activo; el historial y la desactivación son exclusivos del superadmin.

El GLOBAL principal procede de la columna J original. El valor bruto y su versión numérica se conservan; valores no numéricos quedan nulos. E:I alimenta solo un cálculo alternativo (regla del Excel: suma / 5, vacías = 0) y Q:U conserva los niveles fuente. Los programas se identifican por nombre normalizado (sin tildes, mayúsculas ni espacios extra); cada escritura original queda como alias.

`TD PROGRAMAS` es una tabla dinámica guardada en el libro. Se lee sin fila de encabezado (la primera fila puede ser un título o directamente `AÑO`). Se persiste la selección de año y los valores visibles al importar; no se recalcula la tabla dinámica ni reemplaza el histórico de `BD GEN`.

## Razones de esta construcción

- Los DTOs aíslan el contrato HTTP de las entidades ORM y evitan exponer campos internos.
- Los servicios permiten probar reglas de negocio sin pasar por HTTP.
- Los repositorios concentran el acceso a SQLAlchemy o al motor Excel.
- La separación por módulo reduce dependencias cruzadas y facilita agregar capacidades.
- El monolito modular evita el coste operativo de microservicios antes de necesitar escalado o despliegue independiente.
