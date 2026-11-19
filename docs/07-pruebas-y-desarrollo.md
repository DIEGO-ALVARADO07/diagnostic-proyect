# Pruebas y desarrollo

## Pruebas automatizadas

Desde `code/api-reader-excel`, con el entorno virtual activo:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas cubren:

- Hashes de contraseña y permisos por rol.
- Límite de acceso a perfiles y restricciones de edición.
- DTOs de respuesta, incluyendo la ausencia de hashes.
- Login y almacenamiento de solo el hash del token.
- Selección de la primera hoja o de una hoja indicada y errores Excel.
- Contrato de configuración de DB.
- Migración inicial: coincidencia con metadatos ORM, aplicación/reversión en SQLite y cuidado con esquemas parciales.

No se requiere un servidor MySQL para esta suite; las pruebas de persistencia usan SQLite temporal en memoria. La prueba de migración sobre SQLite no reemplaza una validación de despliegue sobre MySQL.

## Ejecutar para desarrollo

Arranca el servidor desde `code/api-reader-excel/core` con las variables de configuración:

```powershell
$env:PYTHONPATH = (Resolve-Path ..).Path
..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

La documentación OpenAPI queda en `http://127.0.0.1:8000/docs`.

## Guía para agregar una funcionalidad

1. Crear o extender el módulo bajo `modules/<nombre>/`.
2. Definir los DTOs request/response necesarios, sin reutilizar entidades ORM como contrato de frontend.
3. Implementar reglas de negocio en `services/`.
4. Implementar acceso a datos o adaptadores en `repositories/`.
5. Mantener las rutas delgadas y registrar el router en `api/__init__.py`.
6. Si se agrega persistencia, definir entidades y una migración versionada; no crear tablas al iniciar la API.
7. Añadir pruebas focalizadas para reglas, contratos y migraciones.

## Limitaciones conocidas

- El módulo Excel responde con todos los registros de la hoja; todavía no expone paginación, procesamiento por lotes ni persistencia.
- La API aplica límite de carga de 30 MB, pero un archivo bajo ese límite todavía puede producir una respuesta JSON grande.
- Python 3.15.2 es la versión del entorno inspeccionado; el proyecto no publica aún un rango oficial de versiones soportadas.
