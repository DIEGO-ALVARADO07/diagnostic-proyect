# Tecnologías, dependencias y bases de datos

## Versiones de referencia

El proyecto declara la versión de API `1.0.0` en `app`. El entorno inspeccionado usa Python `3.15.2`; no hay actualmente un archivo de metadatos que declare un rango formal de versiones soportadas. Las versiones siguientes son las fijadas en el `requirements.txt` inspeccionado.

## Bibliotecas principales

| Biblioteca | Versión fijada | Uso |
|---|---:|---|
| FastAPI | 0.162.4 | Rutas HTTP, dependencias, validación e integración OpenAPI. |
| Uvicorn | 0.54.0 | Servidor ASGI para ejecutar la API. |
| Pydantic | 2.14.3 | Validación de DTOs request/response. |
| pydantic-settings | 2.16.3 | Carga de configuración y variables de entorno. |
| SQLAlchemy | 2.1.9 | Entidades ORM, consultas, sesiones y engine. |
| PyMySQL | 1.2.4 | Driver Python de MySQL para SQLAlchemy. |
| Alembic | 1.16.5 | Versionado y aplicación de cambios de esquema. |
| fastexcel | 0.21.0 | Lectura del contenido de libros Excel. |
| Polars | 2.1.0 | Conversión y manejo tabular de hojas cargadas. |
| python-multipart | 0.0.33 | Parsing de archivos y formularios `multipart/form-data`. |
| cryptography | 50.0.2 | Descifrado Fernet de credenciales de DB cuando están cifradas. |
| python-dotenv | 1.2.4 | Soporte para cargar configuración desde `.env`. |

## Todas las dependencias fijadas

El archivo de dependencias contiene las siguientes versiones exactas; algunas son dependencias indirectas requeridas por las bibliotecas principales:

```text
alembic==1.16.5
annotated-doc==0.0.6
annotated-types==0.8.0
anyio==4.16.0
cffi==2.1.1
click==8.5.1
cryptography==50.0.2
fastapi==0.162.4
fastexcel==0.21.0
h11==0.16.0
idna==3.20
opentelemetry-api==1.45.2
polars==2.1.0
polars-runtime-32==2.1.0
pycparser==3.12
pydantic==2.14.3
pydantic-settings==2.16.3
pydantic_core==2.50.4
PyMySQL==1.2.4
python-dotenv==1.2.4
python-multipart==0.0.33
SQLAlchemy==2.1.9
starlette==1.10.0
typing-inspection==0.4.5
typing_extensions==4.16.0
uvicorn==0.54.0
```

## Bases de datos

- **MySQL** es el motor configurado para la ejecución de la API. La URL se construye con `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y `DB_NAME`; PyMySQL implementa la conexión.
- `AuthBase` reúne las tablas `api_users`, `api_access_tokens` y el esquema relacional del dashboard académico; no reutiliza el `Base` de `core`.
- El dashboard persiste metadatos de importación (`excel_imports`), estudiantes (`academic_students`), etiquetas originales de programas (`academic_programs`), equivalencias de programa confirmables (`academic_program_aliases`), intentos por fila (`academic_results`), referencias visibles de TD (`td_programas_reference`) y el ID del snapshot activo (`excel_dashboard_state`).
- Cada intento BD GEN se identifica por `(import_id, source_row_number)`, no por documento o simulacro. El archivo binario no se conserva; sí se guarda el contenido estructurado requerido para consultas, incluido el payload de origen.
- **SQLite** se usa en pruebas automatizadas con una base temporal en memoria. No es el motor configurado para el despliegue.
- `POST /excel/read` sigue siendo una operación temporal de lectura; `POST /excel/dashboard/import` sí persiste snapshots de resultados e historial.

### Regla de origen de las métricas

- La columna J de `BD GEN` es el puntaje GLOBAL principal. Se almacena su representación original y su valor numérico; si la celda no es numérica, el puntaje numérico queda `NULL` y no participa en los promedios globales.
- Los puntajes de competencia E:I se guardan por separado. Su suma dividida por cinco es solo un cálculo alternativo y no reemplaza J.
- Los niveles Q:U se conservan desde el Excel; no se reconstruyen a partir de los puntajes.
- Los programas mantienen etiquetas exactas. La clave normalizada apoya filtros/búsqueda, pero no combina automáticamente nombres que difieran por tildes, espacios o mayúsculas.
- Existe una tabla para alias confirmados de programa, pero la importación actual no crea ni aplica alias automáticamente.
- `TD PROGRAMAS` es una tabla dinámica: se persiste el año seleccionado y la referencia visible de esa importación. Los históricos se consultan desde BD GEN.

El detalle de columnas, estados e invariantes está en [flujo del dashboard académico](09-flujo-dashboard-academico.md).

## Por qué se eligieron

- **FastAPI + Pydantic:** contratos HTTP tipados y validación automática, además de OpenAPI.
- **SQLAlchemy + PyMySQL:** ORM y driver compatibles con la base MySQL que configura el proyecto.
- **Alembic:** historial auditable y repetible de cambios, en lugar de crear tablas al arrancar la API.
- **fastexcel + Polars:** apertura de libros y conversión tabular separadas del código HTTP; el parseo se ejecuta en thread pool.
- **cryptography:** protege credenciales de configuración cifradas; las contraseñas de cuentas usan PBKDF2 de la biblioteca estándar, no Fernet.
- **Uvicorn:** servidor ASGI usado por FastAPI.

Las dependencias están fijadas para reproducir el entorno probado; actualizar versiones requiere ejecutar las pruebas y revisar compatibilidad antes del despliegue.
