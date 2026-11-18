# Implementación de la API modular

Este documento registra las decisiones aplicadas y el motivo de cada paso. No se modifican archivos del módulo `core`; la API reutiliza su sesión de SQLAlchemy mediante una dependencia diferida.

## Pasos realizados

1. **Separar el punto de entrada de la lógica.** Se reemplazó `main.py` por el paquete `app` con `create_app()` y `app`, y se centralizó el registro de routers en `api`. Esto permite iniciar con `uvicorn app:app` y mantener los módulos independientes.
2. **Definir roles y permisos explícitos.** Se modelaron `superadmin`, `instructor` y `estudiante`. Instructor puede consultar/editar perfiles y subir Excel, pero no crear cuentas ni desactivar usuarios; tampoco puede cambiar la contraseña, usuario o rol de otras cuentas. Estudiante solo consulta y edita su propio perfil. Superadmin puede gestionar cuentas y desactivarlas; no se permite desactivar al último superadmin activo.
3. **Añadir autenticación sin registro público.** El login entrega un token opaco aleatorio de 8 horas; solo se guarda su hash en `api_access_tokens`. Las contraseñas se guardan como PBKDF2-HMAC-SHA256 con salt aleatorio, nunca en texto claro. No se agrega una biblioteca de autenticación ni se expone el alta de superadmins.
4. **Aislar las tablas de la API.** Se definieron `api_users` y `api_access_tokens` con un `DeclarativeBase` propio. La inicialización explícita del primer superadmin crea solo esas tablas; no altera el `Base` de `core` ni usa `create_all()` al iniciar el servidor.
5. **Incorporar procesamiento Excel protegido.** `POST /excel/read` requiere instructor o superadmin, mantiene los formatos intentados en el código original, valida extensión, limita el archivo a 30 MB y permite elegir la hoja por nombre. Si no se indica, lee la primera. El parseo corre fuera del event loop.
6. **Documentar la operación.** Se añadieron pasos de inicialización, ejecución y rutas para que el frontend consuma la API sin acceso directo a MySQL.

## Permisos y rutas

| Acción | Superadmin | Instructor | Estudiante |
|---|---:|---:|---:|
| Iniciar/cerrar sesión | Sí | Sí | Sí |
| Consultar su perfil | Sí | Sí | Sí |
| Editar su perfil | Sí | Sí | Sí |
| Consultar perfiles de otros | Sí | Sí | No |
| Editar perfiles de otros | Sí | Sí (sin cambiar usuario, rol ni contraseña) | No |
| Crear instructor/estudiante | Sí | No | No |
| Desactivar cuentas | Sí | No | No |
| Subir y leer Excel | Sí | Sí | No |

- `POST /auth/login`: recibe `username` y `password`; devuelve `access_token`, `expires_in` y perfil.
- `POST /auth/logout`: revoca el token actual.
- `GET /users/me`, `PATCH /users/me`: perfil propio.
- `GET /users`, `GET /users/{id}`, `PATCH /users/{id}`: consulta/edición según rol.
- `POST /users`: solo superadmin; solo puede crear instructor o estudiante.
- `DELETE /users/{id}`: solo superadmin; desactivación lógica y revocación de sesiones.
- `POST /excel/read`: recibe `file` y un `sheet_name` opcional como `multipart/form-data`; si se omite, lee la primera hoja. La respuesta incluye `available_sheets` y `sheet_read`.
- `GET /health`: comprobación de disponibilidad sin consultar la base.

Las rutas protegidas usan `Authorization: Bearer <access_token>`. Se requiere una contraseña de al menos 12 caracteres al crear o cambiar una cuenta. No existe registro público ni endpoint para crear/promover superadmins.

El frontend debe enviar el archivo y el nombre exacto de la hoja en la misma petición. Si envía un nombre que no existe, la API responde `422` con la lista `available_sheets`.

## Configuración y ejecución

La API usa `core.database.SessionLocal` y no cambia cómo `core.config` carga ni descifra la configuración. En el repositorio, el `.env` existente está dentro de `core/` y la configuración usa la ruta relativa `.env`; por eso, ejecuta los comandos desde `code/api-reader-excel/core`. La base de datos/schema de MySQL debe existir previamente y el usuario configurado debe poder crear tablas. Exporta `APP_MASTER_KEY` en la terminal, nunca en el código.

### Primera ejecución: bootstrap antes de la API

1. Abre PowerShell, ve a `core/`, configura la clave maestra y el `PYTHONPATH`.
2. Define las credenciales temporales del primer superadmin.
3. Ejecuta el bootstrap y confirma que imprima `Cuenta superadmin inicial creada.`. Este comando crea solo las tablas `api_users` y `api_access_tokens`, e inserta la cuenta inicial. **No inicies Uvicorn antes de este paso.**
4. Si el bootstrap termina con error, no continúes al paso de Uvicorn: corrige primero la conexión o configuración.
5. Al terminar correctamente, elimina las variables temporales de bootstrap y arranca la API desde la misma carpeta y terminal.

Ejecuta estos comandos en orden. Reemplaza los valores de ejemplo directamente en la terminal; no guardes la clave ni la contraseña en el repositorio:

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect\code\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-maestra-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path

$env:BOOTSTRAP_SUPERADMIN_USERNAME = "<usuario>"
$env:BOOTSTRAP_SUPERADMIN_EMAIL = "<correo>"
$env:BOOTSTRAP_SUPERADMIN_FULL_NAME = "<nombre>"
$env:BOOTSTRAP_SUPERADMIN_PASSWORD = "<contraseña-de-12-caracteres-o-mas>"

..\venv\Scripts\python.exe -m auth.bootstrap
if ($LASTEXITCODE -ne 0) { throw "El bootstrap falló; no inicies Uvicorn." }

Remove-Item Env:\BOOTSTRAP_SUPERADMIN_USERNAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_EMAIL
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_FULL_NAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_PASSWORD

..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Uvicorn queda ejecutándose en primer plano; abre `/docs` para explorar la API. En arranques posteriores, no vuelvas a ejecutar el bootstrap: abre una terminal, ve a `core/`, configura `APP_MASTER_KEY` y ejecuta solo el último comando de Uvicorn. El servidor no crea las tablas automáticamente.

## Validación

La validación se realiza con el entorno virtual existente y pruebas unitarias centradas en hash de contraseña, roles y selección de la primera hoja. La conexión real a MySQL requiere la llave maestra y credenciales configuradas en el entorno local; no se prueban ni se leen secretos desde este cambio.
