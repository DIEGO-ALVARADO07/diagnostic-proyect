# Organización modular de la API

La API está organizada como un monolito modular: `modules/security` contiene autenticación, roles, permisos y gestión de usuarios; `modules/excel` contiene el procesamiento de hojas de cálculo. `core` conserva la configuración y persistencia compartidas, mientras `api` ensambla los routers y `app` crea la aplicación. Esta separación permite añadir módulos sin convertirlos todavía en servicios independientes.

La guía de integración de la aplicación PHP está en [`front/README.md`](../../front/README.md). Este documento se concentra en el backend, sus rutas, configuración, migraciones y pruebas.

## Capas por módulo

- `routes.py` adapta HTTP: recibe DTOs, invoca servicios y declara los DTOs de respuesta.
- `dtos/requests` valida las entradas; `dtos/responses` limita explícitamente los datos que se entregan al frontend. No se serializan entidades ORM directamente.
- `services` contiene los casos de uso y reglas de negocio.
- `repositories` concentra las consultas y el acceso a datos o al lector de archivos.
- `entities` contiene los modelos ORM (`Account`, `AccessToken`, `AuthBase`) y los tipos del dominio (`Role`, `Permission`). Los módulos anteriores `models.py`, `role.py` y `permission.py` se conservan como fachadas de compatibilidad; las tablas y columnas no cambian.
- `modules/security/migrations` guarda las migraciones Alembic de las tablas de seguridad. Excel no persiste información y por eso su carpeta de migraciones no contiene versiones de esquema.

## Pasos realizados

1. **Separar la composición de los módulos.** `api` reúne los routers de seguridad y Excel; cada módulo conserva sus propias rutas y lógica. `app` expone `create_app()` y `app` sin incorporar reglas de negocio.
2. **Definir roles y permisos explícitos.** Se modelaron `superadmin`, `instructor` y `estudiante`. Instructor puede consultar/editar perfiles y subir Excel, pero no crear cuentas ni desactivar usuarios; tampoco puede cambiar la contraseña, usuario o rol de otras cuentas. Estudiante solo consulta y edita su propio perfil. Superadmin puede gestionar cuentas y desactivarlas; no se permite desactivar al último superadmin activo.
3. **Añadir autenticación sin registro público.** El login entrega un token opaco aleatorio de 8 horas; solo se guarda su hash en `api_access_tokens`. Las contraseñas se guardan como PBKDF2-HMAC-SHA256 con salt aleatorio, nunca en texto claro. No se agrega una biblioteca de autenticación ni se expone el alta de superadmins.
4. **Aislar las tablas de la API.** `api_users` y `api_access_tokens` conservan su `DeclarativeBase` propio. Alembic versiona esas tablas sin alterar el `Base` de `core`; el servidor no crea tablas al iniciar.
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

## Configuración y ejecución en Windows

La API usa `core.database.SessionLocal`. El `.env` debe estar en `core/` porque Pydantic busca la ruta relativa `.env` desde la carpeta de ejecución. Debe contener `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y `DB_NAME`. La base/schema MySQL debe existir antes y el usuario necesita permisos para crear índices y tablas de seguridad. Si `DB_USER` o `DB_PASSWORD` están cifrados con Fernet, define `APP_MASTER_KEY` con la clave entregada por el equipo; no guardes secretos en el repositorio ni los pegues en logs.

### 1. Instalar dependencias

Abre PowerShell en la raíz del proyecto:

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect\back\api-reader-excel
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si todavía no existe `venv`, créalo primero con `python -m venv venv` y luego actívalo e instala las dependencias.

### 2. Primera ejecución en una base nueva

El bootstrap aplica la migración de seguridad y crea el primer superadmin. Ejecuta una sola vez. En la misma terminal:

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect\back\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-maestra-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path

$env:BOOTSTRAP_SUPERADMIN_USERNAME = "<usuario>"
$env:BOOTSTRAP_SUPERADMIN_EMAIL = "<correo>"
$env:BOOTSTRAP_SUPERADMIN_FULL_NAME = "<nombre>"
$env:BOOTSTRAP_SUPERADMIN_PASSWORD = "<contraseña-de-12-caracteres-o-mas>"

..\venv\Scripts\python.exe -m modules.security.bootstrap
if ($LASTEXITCODE -ne 0) { throw "El bootstrap falló; no inicies Uvicorn." }
```

Continúa solo si imprime `Cuenta superadmin inicial creada.`. Si falla, corrige el error de conexión/configuración antes de arrancar la API. El bootstrap es de aprovisionamiento inicial: no lo vuelvas a ejecutar después de que ya exista el superadmin. Las variables `BOOTSTRAP_SUPERADMIN_*` solo entregan las credenciales al proceso una vez; el usuario queda guardado en `api_users` y no se borra al limpiar esas variables.

### 3. Iniciar la API

Desde `core/`, en la terminal anterior, elimina únicamente las variables temporales de bootstrap y arranca el servidor. Esto no elimina la cuenta creada. Conserva `APP_MASTER_KEY` y `PYTHONPATH`, que sí se necesitan para conectar y cargar la aplicación:

```powershell
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_USERNAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_EMAIL
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_FULL_NAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_PASSWORD

..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Deja Uvicorn ejecutándose en primer plano y abre `http://127.0.0.1:8000/docs`. Detén el servidor con `Ctrl+C`.

### 4. Arranques posteriores y nuevas migraciones

No repitas el bootstrap. Para iniciar en una terminal nueva, define solo `APP_MASTER_KEY` y `PYTHONPATH`, desde `core/`, y ejecuta Uvicorn:

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect\back\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-maestra-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path
..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Si se despliega una versión que añade migraciones, aplica primero las pendientes usando la misma configuración y permisos de base de datos:

```powershell
..\venv\Scripts\python.exe -m modules.security.migrations
```

El comando reconoce una base antigua sin historial Alembic solo si encuentra ambas tablas de seguridad y verifica que coincidan con los modelos; si están incompletas o distintas, se detiene sin marcarlas como migradas. El servidor no crea ni migra tablas automáticamente.

### Pruebas

Desde la carpeta del proyecto, activa el entorno virtual y ejecuta:

```powershell
python -m unittest discover -s tests -v
```

## Flujo completo de la API

### Arranque y composición

1. Uvicorn importa `app:app`; `app.create_app()` crea FastAPI y agrega el router central de `api`.
2. `api` ensambla los routers de autenticación, usuarios y Excel. Las reglas de negocio permanecen dentro de sus módulos.
3. Las rutas que requieren base de datos obtienen una sesión con `modules/security/database.py`; esta importa `core.database.SessionLocal` de forma diferida y cierra la sesión al terminar la petición.

### Inicio de sesión y autorización

1. `POST /auth/login` valida el JSON con `LoginRequest`.
2. La ruta delega en `AuthService`; `AccountRepository` busca la cuenta por usuario normalizado.
3. `security.py` verifica la contraseña PBKDF2. Si es válida, se genera un token opaco; `TokenRepository` guarda solo su hash y su vencimiento, y el servicio confirma la transacción.
4. `LoginResponse` contiene el token, su duración y un `UserResponse` que no expone el hash de contraseña.
5. En una ruta protegida, `CurrentAccount` extrae el Bearer token, calcula su hash, verifica que exista, no esté revocado y no haya vencido, y carga la cuenta activa. Las dependencias de roles/permisos rechazan operaciones no autorizadas.
6. `POST /auth/logout` marca como revocado el token autenticado.

### Usuarios

1. FastAPI valida el body con el DTO request correspondiente.
2. La ruta invoca `UserService`, que aplica las reglas de rol y alcance (propia cuenta u otras cuentas).
3. `AccountRepository` y `TokenRepository` concentran lecturas y escrituras. Al crear/cambiar contraseña, el servicio almacena el hash, nunca el valor recibido.
4. El servicio confirma cambios y devuelve DTOs response. Las colisiones de usuario/correo se convierten en `409`; al desactivar un usuario también se revocan sus tokens y no se permite desactivar al último superadmin.

### Lectura de Excel

1. `POST /excel/read` autentica la cuenta y comprueba rol y extensión antes de leer el archivo.
2. La ruta lee como máximo 30 MB más un byte para detectar exceso y arma `ReadWorkbookRequest` con archivo y hoja solicitada.
3. `ExcelService` aplica las reglas de tamaño, formato y autorización; mueve el parseo fuera del event loop.
4. `WorkbookRepository` usa fastexcel para cargar la hoja elegida (o la primera si se omite) y produce la entidad `WorkbookRead`.
5. `ReadWorkbookResponse` limita y tipa los datos devueltos al frontend. El módulo Excel es actualmente sin estado: no guarda el archivo ni los resultados.

### Errores

Los servicios expresan errores esperados como `ApplicationError`. El manejador central en `app` los convierte en respuestas HTTP con el status y detalle definidos; errores inesperados no se transforman silenciosamente en éxitos.

## Validación

La validación incluye pruebas unitarias de roles, servicios, DTOs y lectura Excel, además de comparar la migración inicial con el esquema ORM en SQLite. La conexión real a MySQL requiere la llave maestra y credenciales configuradas en el entorno local; no se prueban ni se leen secretos desde este cambio.
