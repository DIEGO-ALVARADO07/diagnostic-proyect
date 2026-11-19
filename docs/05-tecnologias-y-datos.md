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
- La API crea/gestiona las tablas de seguridad `api_users` y `api_access_tokens`. El esquema de seguridad tiene `AuthBase` propio y no reutiliza el `Base` de `core`.
- **SQLite** se usa en pruebas automatizadas con una base temporal en memoria. No es el motor configurado para el despliegue.
- Excel no persiste archivos, filas, resultados ni históricos, así que no hay tablas ni migraciones de datos Excel actualmente.

## Por qué se eligieron

- **FastAPI + Pydantic:** contratos HTTP tipados y validación automática, además de OpenAPI.
- **SQLAlchemy + PyMySQL:** ORM y driver compatibles con la base MySQL que configura el proyecto.
- **Alembic:** historial auditable y repetible de cambios, en lugar de crear tablas al arrancar la API.
- **fastexcel + Polars:** apertura de libros y conversión tabular separadas del código HTTP; el parseo se ejecuta en thread pool.
- **cryptography:** protege credenciales de configuración cifradas; las contraseñas de cuentas usan PBKDF2 de la biblioteca estándar, no Fernet.
- **Uvicorn:** servidor ASGI usado por FastAPI.

Las dependencias están fijadas para reproducir el entorno probado; actualizar versiones requiere ejecutar las pruebas y revisar compatibilidad antes del despliegue.
