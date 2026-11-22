# Organización modular de la API

La API está organizada como un monolito modular: `modules/security` contiene autenticación, roles, permisos y gestión de usuarios; `modules/excel` contiene el procesamiento de hojas de cálculo. `core` conserva la configuración y persistencia compartidas, mientras `api` ensambla los routers y `app` crea la aplicación. Esta separación permite añadir módulos sin convertirlos todavía en servicios independientes.

La guía de integración de la aplicación PHP está en [`front/README.md`](../../front/README.md). Este documento se concentra en el backend, sus rutas, configuración, migraciones y pruebas.

## Capas por módulo

- `routes.py` adapta HTTP: recibe DTOs, invoca servicios y declara los DTOs de respuesta.
- `dtos/requests` valida las entradas; `dtos/responses` limita explícitamente los datos que se entregan al frontend. No se serializan entidades ORM directamente.
- `services` contiene los casos de uso y reglas de negocio.
- `repositories` concentra las consultas y el acceso a datos o al lector de archivos.
- `entities` contiene los modelos ORM (`Account`, `AccessToken`, `AuthBase`) y los tipos del dominio (`Role`, `Permission`). Los módulos anteriores `models.py`, `role.py` y `permission.py` se conservan como fachadas de compatibilidad; las tablas y columnas no cambian.
- `modules/security/migrations` conserva las migraciones Alembic de seguridad y del dashboard académico; ambas comparten `AuthBase` y se aplican en orden.

## Pasos realizados

1. **Separar la composición de los módulos.** `api` reúne los routers de seguridad y Excel; cada módulo conserva sus propias rutas y lógica. `app` expone `create_app()` y `app` sin incorporar reglas de negocio.
2. **Definir roles y permisos explícitos.** Se modelaron `superadmin`, `instructor` y `estudiante`. Instructor puede consultar/editar perfiles y subir Excel, pero no crear cuentas ni desactivar usuarios; tampoco puede cambiar la contraseña, usuario o rol de otras cuentas. Estudiante solo consulta y edita su propio perfil. Superadmin puede gestionar cuentas y desactivarlas; no se permite desactivar al último superadmin activo.
3. **Añadir autenticación sin registro público.** El login entrega un token opaco aleatorio de 8 horas; solo se guarda su hash en `api_access_tokens`. Las contraseñas se guardan como PBKDF2-HMAC-SHA256 con salt aleatorio, nunca en texto claro. No se agrega una biblioteca de autenticación ni se expone el alta de superadmins.
4. **Aislar las tablas de la API.** `api_users`, `api_access_tokens` y el esquema académico conservan su `DeclarativeBase` propio. Alembic versiona esas tablas sin alterar el `Base` de `core`; el servidor no crea tablas al iniciar.
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
| Subir, leer y consultar Excel/dashboard | Sí | Sí | No |

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

Todas las tareas se ejecutan con [`tasks.ps1`](./tasks.ps1), desde la carpeta del backend. El script usa el Python del `venv` y define `PYTHONPATH` por sí mismo, así que no hace falta activar el entorno ni moverse a `core/`.

| Comando | Qué hace |
|---|---|
| `.\tasks.ps1 install` | Crea el `venv` si no existe e instala `requirements.txt`. |
| `.\tasks.ps1 migrate` | Aplica las migraciones Alembic pendientes. |
| `.\tasks.ps1 bootstrap` | Aplica migraciones y crea el primer superadmin (una sola vez). |
| `.\tasks.ps1 test` | Ejecuta las pruebas automatizadas. |
| `.\tasks.ps1 run` | Arranca Uvicorn con recarga en `http://127.0.0.1:8000` (`-Port` y `-BindHost` son opcionales). |

Si PowerShell bloquea el script por la política de ejecución, permite scripts locales para tu usuario con `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 1. Configuración (`core/.env`)

La configuración se lee de `core/.env` (ruta absoluta, no depende de la carpeta desde donde se ejecute). **Este archivo no se versiona.** Créalo a partir de la plantilla:

```powershell
Copy-Item core\.env.example core\.env
```

Debe contener `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y `DB_NAME`; opcionalmente `LOG_LEVEL` (`INFO` por defecto). La base/schema MySQL debe existir antes y el usuario necesita permisos para crear tablas e índices. Si `DB_USER` o `DB_PASSWORD` están cifrados con Fernet (empiezan por `gAAAAAB`), define `APP_MASTER_KEY` en la terminal antes de ejecutar cualquier tarea; `tasks.ps1` avisa si falta:

```powershell
$env:APP_MASTER_KEY = "<clave-maestra-entregada-por-el-equipo>"
```

No guardes secretos en el repositorio ni los pegues en logs.

### 2. Instalar dependencias

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect\back\api-reader-excel
.\tasks.ps1 install
```

### 3. Primera ejecución en una base nueva

El bootstrap aplica las migraciones y crea el primer superadmin. Ejecútalo una sola vez:

```powershell
.\tasks.ps1 bootstrap
```

Pide usuario, correo, nombre y contraseña (oculta, mínimo 12 caracteres). Si ya existen las variables `BOOTSTRAP_SUPERADMIN_USERNAME`, `BOOTSTRAP_SUPERADMIN_EMAIL`, `BOOTSTRAP_SUPERADMIN_FULL_NAME` y `BOOTSTRAP_SUPERADMIN_PASSWORD`, las usa sin preguntar. Al terminar, con éxito o con error, borra esas variables de la terminal. Continúa solo si imprime `Cuenta superadmin inicial creada.`; no lo vuelvas a ejecutar cuando ya exista un superadmin.

### 4. Iniciar la API

```powershell
.\tasks.ps1 run
```

Abre `http://127.0.0.1:8000/docs`. Detén el servidor con `Ctrl+C`. Los logs de la aplicación (por ejemplo, los tiempos de lectura de Excel) aparecen en la misma terminal con el nivel de `LOG_LEVEL`.

### 5. Nuevas migraciones

Si se despliega una versión que añade migraciones, aplícalas antes de arrancar:

```powershell
.\tasks.ps1 migrate
```

El comando reconoce una base antigua sin historial Alembic solo si encuentra ambas tablas de seguridad y verifica que coincidan con los modelos. En ese caso marca la revisión inicial de seguridad (`0001`) y aplica las siguientes, incluida la persistencia académica; si el esquema de seguridad está incompleto o distinto, o ya existen tablas académicas sin historial, se detiene sin marcarlas como migradas. El servidor no crea ni migra tablas automáticamente.

## Dashboard histórico de TD PROGRAMAS

La importación histórica mantiene intacto `POST /excel/read` y agrega estas rutas, protegidas con Bearer:

- `POST /excel/dashboard/import`: recibe `file` en los formatos permitidos por el servicio Excel. Abre el libro una vez y procesa únicamente `BD GEN` y `TD PROGRAMAS`.
- `GET /excel/dashboard/active`: devuelve el snapshot activo.
- `GET /excel/dashboard/imports?limit=20`: solo `superadmin`; devuelve importaciones no desactivadas, con el identificador activo.
- `GET /excel/dashboard/admin/imports?limit=100`: solo para `superadmin`; incluye todos los estados y reporta `DELETED` para importaciones desactivadas.
- `DELETE /excel/dashboard/imports/{import_id}`: solo `superadmin`; desactiva lógicamente una importación `ACTIVE`, `HISTORICAL` o `FAILED`, conservando el snapshot y marcando `deleted_at`. Si era activa, se limpia `active_import_id`; las importaciones en proceso o validadas no se pueden desactivar.
- `GET /excel/dashboard/{import_id}`: devuelve filtros, indicadores globales y programas paginados. `instructor` solo puede consultar el snapshot activo; `superadmin` puede consultar snapshots históricos disponibles. El tamaño predeterminado y máximo es **50 programas**.
- `GET /excel/dashboard/{import_id}/programs/{program_id}`: devuelve métricas del programa, comparación institucional y filas de resultados. Admite `year`, `simulation`, `group`, `semester`, `test_type`, `presented`, `search`, `page` y `page_size`.
- `GET /excel/dashboard/{import_id}/students/{document}`: devuelve el historial del documento y su comparación con el promedio de programa de cada intento.

El dashboard guarda snapshots normalizados en MySQL y no guarda el archivo binario. El SHA-256 del contenido evita duplicar una importación idéntica. La carga registra `PROCESSING`, inserta resultados y referencia visible de `TD PROGRAMAS` en una transacción y solo activa el snapshot después de validarlo; una carga fallida se registra como `FAILED` sin activar ni dejar resultados parciales. La tabla `excel_dashboard_state` serializa el cambio del snapshot activo. Los snapshots previos se conservan como `HISTORICAL`. La desactivación lógica no elimina filas: los endpoints normales omiten el snapshot y responden `404` ante consultas directas; solo el historial administrativo muestra su estado `DELETED`.

Cada intento de `BD GEN` conserva su fila de origen; las filas no se deduplican por documento o simulacro. Los programas se distinguen por su etiqueta original; no se fusionan automáticamente por tildes, mayúsculas ni espacios. Se preservan los niveles fuente Q:U. El puntaje GLOBAL principal se obtiene de J; queda nulo si J no es numérica y los agregados históricos omiten esos valores. El cálculo alternativo desde E:I se conserva separado y nunca sustituye a J. Las métricas se calculan sobre registros `APLICA SIMULACRO = Si`; las desviaciones son poblacionales y requieren dos o más valores. Los niveles fuente faltantes se presentan como `Sin resultado`.

### Auditoría del libro CORHUILA revisado

En el archivo revisado, `TD PROGRAMAS` es una tabla dinámica cuyo filtro de página usa `AÑO`; la selección guardada es `2026`. Su caché de pivote tiene como origen `BD GEN` y contiene los años 2024, 2025 y 2026. El importador no depende de recalcular esa tabla dinámica: reconstruye los tres años desde `BD GEN` y contrasta los bloques visibles del año guardado. No ejecuta macros ni usa las hojas auxiliares, fórmulas externas o vínculos externos.

La respuesta de importación incluye `source_audit`, con los años de `BD GEN`, el año visible de `TD PROGRAMAS` y las métricas que pueden compararse por etiqueta exacta de programa y simulacro. Las diferencias se reportan y no se corrigen ni se mezclan automáticamente. Las filas sin documento siguen siendo intentos y cuentan en presentaciones si aplican, pero no se incluyen en estudiantes únicos ni en búsquedas por documento.

### Pruebas

Desde la carpeta del backend:

```powershell
.\tasks.ps1 test
```

Las pruebas no necesitan `core/.env` ni conexión a MySQL.

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
5. `ReadWorkbookResponse` limita y tipa los datos devueltos al frontend. `POST /excel/read` no persiste; la importación histórica del dashboard sí guarda los resultados y su referencia en tablas académicas versionadas por Alembic.

### Errores

Los servicios expresan errores esperados como `ApplicationError`. El manejador central en `app` los convierte en respuestas HTTP con el status y detalle definidos; errores inesperados no se transforman silenciosamente en éxitos.

## Validación

La validación incluye pruebas unitarias de roles, servicios, DTOs y lectura Excel, además de comparar la migración inicial con el esquema ORM en SQLite. La conexión real a MySQL requiere la llave maestra y credenciales configuradas en el entorno local; no se prueban ni se leen secretos desde este cambio.
