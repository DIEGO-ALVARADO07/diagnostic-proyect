# Instalación, inicialización y operación

## Requisitos

- Windows y PowerShell (los comandos siguientes usan rutas de Windows).
- Python disponible. El entorno revisado para esta documentación usa Python `3.15.2`; el proyecto no declara formalmente un rango mínimo/máximo de Python.
- MySQL accesible y una base/schema creada antes de ejecutar migraciones.
- Credenciales `DB_*` en `code/api-reader-excel/core/.env`.
- `APP_MASTER_KEY` cuando el usuario o contraseña de base de datos en `.env` estén cifrados con Fernet.

No se deben guardar llaves, contraseñas ni credenciales de bootstrap en el repositorio.

## Instalar dependencias

Abre PowerShell en `code/api-reader-excel`:

```powershell
Set-Location <ruta-del-repositorio>\code\api-reader-excel

# Solo si el entorno virtual aún no existe:
python -m venv venv

.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` fija las versiones iniciales de las bibliotecas instaladas. Para reproducir el entorno, activa el mismo virtualenv antes de instalar o ejecutar comandos.

## Variables de entorno

`core/.env` se lee usando una ruta relativa. Por eso los comandos que cargan configuración de base de datos se ejecutan desde `code/api-reader-excel/core`.

| Variable | Uso |
|---|---|
| `DB_USER` | Usuario MySQL. |
| `DB_PASSWORD` | Contraseña MySQL. |
| `DB_HOST` | Host MySQL. |
| `DB_PORT` | Puerto MySQL. |
| `DB_NAME` | Nombre de una base/schema ya creada. |
| `APP_MASTER_KEY` | Clave Fernet para descifrar credenciales cifradas, si aplica. |
| `PYTHONPATH` | Raíz de `code/api-reader-excel`, para importar `core` y `modules` ejecutando desde `core`. |

## Primera instalación en una base nueva

1. Crea la base/schema en MySQL y confirma los valores de `core/.env`.
2. Activa el virtualenv e instala las dependencias.
3. Desde PowerShell, ejecuta el bootstrap en `core/`:

```powershell
Set-Location <ruta-del-repositorio>\code\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path

$env:BOOTSTRAP_SUPERADMIN_USERNAME = "<usuario>"
$env:BOOTSTRAP_SUPERADMIN_EMAIL = "<correo>"
$env:BOOTSTRAP_SUPERADMIN_FULL_NAME = "<nombre>"
$env:BOOTSTRAP_SUPERADMIN_PASSWORD = "<contraseña-de-12-caracteres-o-mas>"

..\venv\Scripts\python.exe -m modules.security.bootstrap
if ($LASTEXITCODE -ne 0) { throw "El bootstrap falló; no inicies Uvicorn." }
```

El comando aplica la migración de seguridad y crea la cuenta inicial. Continúa solo si imprime `Cuenta superadmin inicial creada.`. El bootstrap es de una sola vez; no vuelve a ejecutarse cuando ya existe el superadmin.

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
Set-Location <ruta-del-repositorio>\code\api-reader-excel\core
$env:APP_MASTER_KEY = "<clave-entregada-por-el-equipo>"
$env:PYTHONPATH = (Resolve-Path ..).Path
..\venv\Scripts\python.exe -m uvicorn app:app --app-dir .. --reload --reload-dir ..
```

Si las credenciales de base de datos son texto claro, `APP_MASTER_KEY` no es necesaria para descifrarlas. Debe estar presente si están cifradas.

## Base ya utilizada o actualización de esquema

Antes de una versión que añade migraciones, aplica las pendientes desde `core/` con `APP_MASTER_KEY` y `PYTHONPATH` configurados:

```powershell
..\venv\Scripts\python.exe -m modules.security.migrations
```

Una base antigua sin historial Alembic se reconoce solo si ambas tablas de seguridad existen y coinciden con los modelos. Un esquema incompleto o distinto produce un error; respalda los datos y revisa el esquema antes de continuar. No ejecutes el bootstrap solo para actualizar migraciones.

## Ejecutar pruebas

Desde `code/api-reader-excel` con el virtualenv activo:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan SQLite en memoria para comprobar entidades y migraciones; no requieren conectar al MySQL de producción.
