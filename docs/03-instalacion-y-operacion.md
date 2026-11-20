# Instalación, inicialización y operación

## Requisitos

- Windows y PowerShell (los comandos siguientes usan rutas de Windows).
- Python disponible. El entorno revisado para esta documentación usa Python `3.15.2`; el proyecto no declara formalmente un rango mínimo/máximo de Python.
- MySQL accesible y una base/schema creada antes de ejecutar migraciones.
- Credenciales `DB_*` en `back/api-reader-excel/core/.env`.
- `APP_MASTER_KEY` cuando el usuario o contraseña de base de datos en `.env` estén cifrados con Fernet.

No se deben guardar llaves, contraseñas ni credenciales de bootstrap en el repositorio.

## Instalar dependencias

Abre PowerShell en `back/api-reader-excel`:

```powershell
Set-Location <ruta-del-repositorio>\back\api-reader-excel

# Solo si el entorno virtual aún no existe:
python -m venv venv

.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` fija las versiones iniciales de las bibliotecas instaladas. Para reproducir el entorno, activa el mismo virtualenv antes de instalar o ejecutar comandos.

## Variables de entorno

La configuración actual resuelve `core/.env` junto a `core/config.py`, independientemente de la carpeta de trabajo. No copies credenciales a este documento; configura el `.env` local en cada equipo. Al ejecutar módulos desde `core/`, define `PYTHONPATH` con la raíz de `back/api-reader-excel`.

| Variable | Uso |
|---|---|
| `DB_USER` | Usuario MySQL. |
| `DB_PASSWORD` | Contraseña MySQL. |
| `DB_HOST` | Host MySQL. |
| `DB_PORT` | Puerto MySQL. |
| `DB_NAME` | Nombre de una base/schema ya creada. |
| `APP_MASTER_KEY` | Clave Fernet para descifrar credenciales cifradas, si aplica. |
| `PYTHONPATH` | Raíz de `back/api-reader-excel`, para importar `core` y `modules` ejecutando desde `core`. |

## Primera instalación en una base nueva

1. Crea la base/schema en MySQL y confirma los valores de `core/.env`.
2. Activa el virtualenv e instala las dependencias.
3. Desde PowerShell, ejecuta el bootstrap en `core/`:

```powershell
Set-Location <ruta-del-repositorio>\back\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path

$env:BOOTSTRAP_SUPERADMIN_USERNAME = "<usuario>"
$env:BOOTSTRAP_SUPERADMIN_EMAIL = "<correo>"
$env:BOOTSTRAP_SUPERADMIN_FULL_NAME = "<nombre>"
$env:BOOTSTRAP_SUPERADMIN_PASSWORD = "<contraseña-de-12-caracteres-o-mas>"

..\venv\Scripts\python.exe -m modules.security.bootstrap
if ($LASTEXITCODE -ne 0) { throw "El bootstrap falló; no inicies Uvicorn." }
```

El comando aplica todas las migraciones Alembic pendientes —incluido el esquema del dashboard académico— y crea la cuenta inicial. Continúa solo si imprime `Cuenta superadmin inicial creada.`. El bootstrap es de una sola vez; no vuelve a ejecutarse cuando ya existe el superadmin.

4. Quita las variables temporales de bootstrap y arranca la API en la misma terminal:

```powershell
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_USERNAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_EMAIL
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_FULL_NAME
Remove-Item Env:\BOOTSTRAP_SUPERADMIN_PASSWORD

..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Limpiar las variables no borra el superadmin de `api_users`. Conserva `APP_MASTER_KEY` y `PYTHONPATH` mientras el servidor corre. Abre `http://127.0.0.1:8000/docs`; detén el servidor con `Ctrl+C`.

## Arranques posteriores

No repitas el bootstrap. En una terminal nueva:

```powershell
Set-Location <ruta-del-repositorio>\back\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path
..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Si las credenciales de base de datos son texto claro, `APP_MASTER_KEY` no es necesaria para descifrarlas. Debe estar presente si están cifradas.

## Base ya utilizada o actualización de esquema

Antes de una versión que añade migraciones, aplica las pendientes con el entorno virtual del proyecto y las variables de configuración correspondientes. Desde `back/api-reader-excel/`:

```powershell
.\venv\Scripts\python.exe -m modules.security.migrations
```

También se puede ejecutar desde `core/` con `..\venv\Scripts\python.exe -m modules.security.migrations`. Usa este wrapper en lugar de `python -m alembic upgrade head`: el servicio valida los esquemas legacy antes de aplicar cambios. Una base antigua con las dos tablas de seguridad y sin historial Alembic se reconoce solo si coincide con sus modelos. En ese caso se marca `0001_security_tables` y se aplican las revisiones restantes. Si la seguridad está incompleta o distinta, o si junto a esa base legacy ya hay tablas académicas sin historial, el comando aborta sin marcarla. Un esquema con tablas académicas pero sin el conjunto de seguridad legacy no se adopta automáticamente: respáldalo y revísalo antes de intentar migrar. No ejecutes el bootstrap solo para actualizar migraciones.

La migración `0002_academic_dashboard` crea las tablas de importaciones, estudiantes, programas, resultados, referencia de `TD PROGRAMAS` y el registro que identifica el snapshot activo. La revisión `0003_soft_delete_excel_imports` añade `deleted_at` para desactivación lógica. Ejecuta las migraciones antes de arrancar la nueva versión de la API; el servidor no crea ni modifica tablas automáticamente.

Para cargar y consultar el dashboard, usa una cuenta `instructor` o `superadmin` y sigue la [guía del flujo completo](09-flujo-dashboard-academico.md). En resumen: importa el archivo por `POST /excel/dashboard/import`, consulta `GET /excel/dashboard/active` y navega de global a programa y estudiante usando el mismo `import_id`.

## Ejecutar pruebas

Desde `back/api-reader-excel` con el virtualenv activo:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan SQLite en memoria para comprobar entidades, snapshots, métricas e historial de migraciones; no requieren conectar al MySQL de producción.
