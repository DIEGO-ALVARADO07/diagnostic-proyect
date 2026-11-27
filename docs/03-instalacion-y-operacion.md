# Instalación, uso y operación

> Actualizado el 27 de noviembre de 2026 (código en la rama `dev`, commit `543d7fb`). Versión paso a paso para personas no técnicas: [Manual de instalación](manuales/02-manual-de-instalacion.md).


Esta guía lleva desde un equipo vacío hasta usar el dashboard: instalar, configurar, crear la base, arrancar la API y el frontend, importar el Excel y mantener el sistema actualizado. Todos los comandos son de **PowerShell en Windows**.

## Resumen rápido

Si ya tienes Python, MySQL y la clave maestra, desde `back/api-reader-excel`:

```powershell
.\tasks.ps1 install
Copy-Item core\.env.example core\.env      # y complétalo
$env:APP_MASTER_KEY = "<clave>"            # solo si core\.env va cifrado
.\tasks.ps1 bootstrap                      # solo la primera vez
.\tasks.ps1 run
```

Abre `http://127.0.0.1:8000/docs` (API) y arranca el frontend como se explica en [Paso 6](#paso-6-arrancar-el-frontend).

## Requisitos

| Requisito | Detalle |
|---|---|
| Windows + PowerShell | Los scripts y comandos usan PowerShell (Windows PowerShell 5.1 o PowerShell 7). |
| Python | Entorno probado: Python `3.15.2`. El proyecto todavía no declara un rango oficial; usa la misma versión si puedes. |
| MySQL | Un servidor accesible y una base/schema **ya creada**. El usuario necesita permisos para crear tablas e índices. |
| PHP 7.4+ con cURL | Solo para el frontend (`front/`). |
| `APP_MASTER_KEY` | Solo si las credenciales de `core/.env` están cifradas con Fernet. Se pide al administrador por un canal privado. |

Nunca guardes contraseñas, la clave maestra ni el `core/.env` en Git o en estos documentos. El `.gitignore` del backend ya excluye cualquier `.env`.

## El script `tasks.ps1`

Todas las tareas del backend se ejecutan con `back/api-reader-excel/tasks.ps1`. El script usa el Python del `venv` y prepara `PYTHONPATH` por sí mismo: **no hace falta activar el entorno ni moverse a `core/`**.

| Comando | Qué hace |
|---|---|
| `.\tasks.ps1 install` | Crea el `venv` si no existe e instala `requirements.txt`. |
| `.\tasks.ps1 migrate` | Aplica las migraciones pendientes de la base de datos. |
| `.\tasks.ps1 bootstrap` | Aplica migraciones y crea el primer superadmin (una sola vez). |
| `.\tasks.ps1 run` | Arranca la API con recarga automática en `http://127.0.0.1:8000`. Opcional: `-Port 8080`, `-BindHost 0.0.0.0`. |
| `.\tasks.ps1 test` | Ejecuta las pruebas automatizadas (no necesitan MySQL). |
| `.\tasks.ps1 backup` | Copia de seguridad completa de la base con `mysqldump`. Opcional: `-Label antes-0011` para nombrar la copia. |
| `.\tasks.ps1 backup-daily` | Copia con la etiqueta `diario` **solo si los datos cambiaron** desde la última copia; si no, no crea archivo. Opcional: `-Keep 30` para conservar solo las 30 copias diarias más recientes. |
| `.\tasks.ps1 schedule-backup` | Programa `backup-daily` en Windows todos los días (por defecto a las 22:00; en este equipo, `-At 02:30`). |
| `.\tasks.ps1 unschedule-backup` | Quita la tarea programada. Las copias ya creadas se conservan. |
| `.\tasks.ps1 reset` | **Vacía todos los datos académicos** para empezar desde cero. Antes hace una copia `antes-vaciar` y pide escribir el nombre de la base. Conserva las cuentas; con `-IncludeUsers` también las borra. |
| `.\tasks.ps1 help` | Muestra la ayuda. |

Antes de `run`, `migrate` y `bootstrap`, el script comprueba que exista `core/.env` y que esté definida `APP_MASTER_KEY` cuando las credenciales están cifradas. Si falta algo, se detiene con un mensaje claro en lugar de arrancar a medias.

## Paso 1. Obtener el código

```powershell
git clone https://github.com/DIEGO-ALVARADO07/diagnostic-proyect.git
Set-Location diagnostic-proyect
git switch dev
Set-Location back\api-reader-excel
```

Si PowerShell bloquea el script (`no se puede cargar ... porque la ejecución de scripts está deshabilitada`), permite scripts locales para tu usuario una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Paso 2. Instalar dependencias

```powershell
.\tasks.ps1 install
```

Crea `venv/` (si no existe), actualiza `pip` e instala las versiones fijadas en `requirements.txt`.

## Paso 3. Configurar `core/.env`

La configuración se lee siempre de `back/api-reader-excel/core/.env` (ruta absoluta; no importa desde qué carpeta se ejecute). Créalo a partir de la plantilla:

```powershell
Copy-Item core\.env.example core\.env
notepad core\.env
```

| Variable | Obligatoria | Uso |
|---|---|---|
| `DB_USER` | Sí | Usuario de MySQL. Texto plano o cifrado con Fernet (empieza por `gAAAAAB`). |
| `DB_PASSWORD` | Sí | Contraseña de MySQL. Texto plano o cifrada. |
| `DB_HOST` | Sí | Host de MySQL, p. ej. `127.0.0.1`. |
| `DB_PORT` | Sí | Puerto, p. ej. `3306`. |
| `DB_NAME` | Sí | Nombre de la base/schema ya creada. |
| `LOG_LEVEL` | No | `DEBUG`, `INFO` (por defecto), `WARNING` o `ERROR`. |

Variables de la **terminal** (no van en el archivo):

| Variable | Cuándo |
|---|---|
| `APP_MASTER_KEY` | Si `DB_USER`/`DB_PASSWORD` están cifrados. Defínela en cada terminal nueva: `$env:APP_MASTER_KEY = "<clave>"`. |
| `LOG_LEVEL` | Opcional; si se define en la terminal tiene prioridad sobre `core/.env`. |

**Antes de cada migración**, haz una copia de seguridad: `.\tasks.ps1 backup -Label antes-<migración>`. Se guarda en `%USERPROFILE%\respaldos\<base>` (fuera del repositorio) y se restaura en HeidiSQL con *Archivo → Ejecutar archivo SQL*.

## Paso 4. Primera vez: crear tablas y superadmin

Con la base vacía (ya creada en MySQL) y `APP_MASTER_KEY` definida si aplica:

```powershell
.\tasks.ps1 bootstrap
```

El script pide usuario, correo, nombre completo y contraseña del superadmin (oculta, mínimo 12 caracteres). Si ya existen las variables `BOOTSTRAP_SUPERADMIN_USERNAME`, `BOOTSTRAP_SUPERADMIN_EMAIL`, `BOOTSTRAP_SUPERADMIN_FULL_NAME` y `BOOTSTRAP_SUPERADMIN_PASSWORD`, las usa sin preguntar. Al terminar, con éxito o con error, **borra esas variables** de la terminal.

Qué hace:

1. Aplica todas las migraciones (`0001` a `0013`).
2. Crea la cuenta `superadmin`.

Continúa solo si imprime `Cuenta superadmin inicial creada.`. Es un paso **de una sola vez**: si ya existe un superadmin, se cancela sin cambiar nada. Las demás cuentas (instructores y estudiantes) se crean después desde el frontend o con `POST /users`.

## Paso 5. Arrancar la API

```powershell
.\tasks.ps1 run
```

- Documentación interactiva: `http://127.0.0.1:8000/docs`.
- Comprobación rápida: `http://127.0.0.1:8000/health` debe responder `{"status":"ok"}` (no consulta la base).
- Los logs de la aplicación salen en la misma terminal, por ejemplo los tiempos de lectura de Excel o `Dashboard dataset loaded from database`.
- Detén el servidor con `Ctrl+C`.

En cada terminal nueva solo necesitas repetir `$env:APP_MASTER_KEY = "<clave>"` (si aplica) y `.\tasks.ps1 run`. **No** repitas el bootstrap.

## Paso 6. Arrancar el frontend

El frontend PHP llama a la API en `http://127.0.0.1:8000` (constante `API_BASE_URL` de `front/api_client.php`; cámbiala si usas otro host o puerto). Desde la **raíz del repositorio** y en otra terminal:

```powershell
php -S 127.0.0.1:8081
```

Abre `http://127.0.0.1:8081/front/login.php` e inicia sesión con el superadmin. En Apache/Laragon usa la raíz del repositorio como *document root*. Más detalles en [Frontend PHP](08-frontend.md).

## Uso diario

| Rol | Puede |
|---|---|
| `superadmin` | Todo: cuentas, importar, consultar, estudiantes, cursos; además subir y consultar matriculados, ver y habilitar cursos eliminados, y desactivar o restaurar importaciones. |
| `instructor` | Importar ESE y CORHUILA, consultar el dashboard, ESE y CORHUILA, asignar el programa a los "Sin programa", ver estudiantes por nivel, y crear, llenar y eliminar cursos. |
| `estudiante` | Ver y editar su perfil. |

### Subir matriculados (superadmin)

Antes de CORHUILA, sube en **Matriculados** el archivo oficial de matriculados del periodo (o `POST /enrollment/import`). De ahí salen el programa, el documento y el semestre de los estudiantes de CORHUILA. Detalle en el [Manual de administrador](manuales/03-manual-de-administrador.md).

### Importar el Excel académico

Desde **Importar Excel** (o `POST /excel/dashboard/import`) elige la **prueba** (ESE o CORHUILA), el **periodo** (solo el actual o el anterior) y el archivo (`.xlsx`, `.xlsm`, `.xls` u `.ods`, máximo 30 MB). ESE debe traer las hojas `BD GEN` y `TD PROGRAMAS` y contiene todo el histórico; CORHUILA es la hoja `Calificaciones` exportada de Moodle, un archivo por periodo. La API:


1. calcula la huella SHA-256: si el mismo archivo ya se importó, devuelve esa importación en lugar de duplicarla;
2. lee **solo** las hojas `BD GEN` y `TD PROGRAMAS` (no ejecuta macros ni guarda el archivo);
3. guarda cada fila como un intento y activa la nueva versión; la anterior pasa a histórica.

Reglas de datos que conviene conocer (detalle en [Flujo del dashboard](09-flujo-dashboard-academico.md)):

- **Programas:** nombres que solo difieren en tildes, mayúsculas o espacios son el mismo programa (`INGENIERIA DE SISTEMAS` = `INGENIERÍA DE SISTEMAS`). Se muestra el nombre de `TD PROGRAMAS`, o la variante con tildes. Las filas no se suman entre sí: cada intento se conserva y los promedios se calculan sobre todas las filas del programa.
- **Semestres:** `4` y `SEMESTRE 4` son el mismo semestre.
- **GLOBAL:** se usa la columna GLOBAL del Excel. El cálculo alternativo sigue la regla institucional (suma de las 5 competencias / 5, vacías = 0).
- **Códigos `N`, `N/A`, `P`** en los puntajes cuentan como "sin puntaje" y se informan en la auditoría (`source_audit.data_quality`) para revisarlos.

La respuesta (y la pantalla) incluye una **auditoría** que compara `TD PROGRAMAS` con lo calculado desde `BD GEN`. Las diferencias se informan, no bloquean la importación. Con el libro CORHUILA revisado aparecen 14 diferencias en `average_global` porque `TD PROGRAMAS` promedia también a quienes no presentaron (GLOBAL = 0), mientras la API promedia solo a quienes presentaron.

### Consultar los resultados

- **Dashboard:** ESE y CORHUILA lado a lado en el último periodo; filtros Año → Periodo → Momento → Programa.
- **ESE:** histórico, por programa y por estudiante.
- **Matriculados** (superadmin): el archivo oficial de cada periodo, con filtros.
- **CORHUILA:** el periodo, con filtros de programa y semestre, búsqueda de estudiantes, detalle por programa y la lista "Sin programa".
- **Estudiantes:** todos los de los Excel, por nivel.
- **Cursos:** por nivel y materia.

Detalle de cada pantalla en el [Manual de usuario](manuales/01-manual-de-usuario.md).

### Desactivar o restaurar una importación (superadmin)

En el módulo **Importaciones**. La desactivación es lógica y guarda quién y cuándo. **Restaurar** la vuelve activa si su prueba y periodo no tienen otra; si después se subió una más reciente, queda histórica.


## Actualizar a una versión nueva

1. Trae el código: `git pull` en la rama `dev`.
2. Reinstala dependencias por si cambiaron: `.\tasks.ps1 install`.
3. **Haz una copia de seguridad de la base** si la versión trae migraciones que transforman datos (ver tabla).
4. Aplica las migraciones **antes** de arrancar:

   ```powershell
   $env:APP_MASTER_KEY = "<clave>"
   .\tasks.ps1 migrate
   ```

5. Arranca con `.\tasks.ps1 run`.

El servidor nunca crea ni modifica tablas por sí solo. Usa siempre `.\tasks.ps1 migrate` (equivale a `python -m migrations`) en lugar de `alembic upgrade head`: el comando valida antes las bases antiguas sin historial.

| Migración | Qué hace | ¿Respaldo antes? |
|---|---|---|
| `0001_security_tables` | Usuarios y tokens. | — |
| `0002_academic_dashboard` | Esquema académico del dashboard. | — |
| `0003_soft_delete_excel_imports` | Añade `deleted_at` a las importaciones. | Recomendado |
| `0004_unify_programs` | **Fusiona** programas duplicados por tildes/mayúsculas/espacios y vuelve única la clave. No se revierte la fusión. | **Obligatorio** |
| `0005_sources_periods_moments` | Prueba (ESE o CORHUILA), periodo y momento; una importación activa por espacio. | Recomendado |
| `0006_student_identity_by_email` | Estudiantes identificados por correo. | **Obligatorio** |
| `0007_document_identity` | Identidad por documento con los correos como alias; Momento 4. | **Obligatorio** |
| `0008_manual_program` | Programa manual de los estudiantes "Sin programa". | Recomendado |
| `0009_courses` | Tablas de cursos e inscripciones. | — |
| `0010_soft_delete_audit` | Auditoría de eliminar y restaurar (cursos e importaciones). | — |
| `0011_course_details` | Materia, descripción y metodología de los cursos. | — |
| `0012_enrollment_records` | Tablas de matriculados (cargas por periodo y filas). | — |
| `0013_enrollment_matching` | Tipo de documento del estudiante y programas extra de un resultado (doble programa). | Recomendado |


> **Pendiente en las bases existentes:** la migración `0004` se publicó el 22/11/2026. Hasta aplicarla, los programas de las importaciones anteriores siguen separados por escritura y la base no impide duplicados nuevos.

## Respaldos y vaciado de la base

Las copias se guardan en `%USERPROFILE%\respaldos\<base>` (por ejemplo, `C:\Users\<usuario>\respaldos\excel_reader`), **fuera del repositorio**: contienen datos personales y nunca deben ir a Git. Cada copia es un `.sql` con `DROP DATABASE` + `CREATE DATABASE`; al restaurarla (HeidiSQL → *Archivo → Ejecutar archivo SQL*), la base vuelve exactamente al estado de la copia.

### Copia manual

    .\tasks.ps1 backup -Label antes-0011

Úsala antes de cada migración o de cualquier cambio grande. El nombre queda como `excel_reader_2026-11-26_1519_antes-0011.sql`.

### Copia diaria automática (solo si hubo cambios)

    .\tasks.ps1 backup-daily

- Calcula una huella de los datos (`CHECKSUM TABLE` de cada tabla) y la compara con la de la última copia, guardada en `.ultimo-respaldo.json` en la misma carpeta.
- **Si nada cambió, no crea otro archivo**, para no llenar el disco. Hay cambio cuando se sube un Excel, se crea o elimina un curso, se asigna un programa, etc.
- **Iniciar sesión no cuenta como cambio**: la tabla de sesiones (`api_access_tokens`) no entra en la huella.
- Cualquier copia, manual o diaria, actualiza la huella.
- Con `-Keep 30` se borran las copias `diario` más viejas y quedan las 30 más recientes. Las copias manuales (`antes-…`) nunca se borran. Sin `-Keep` no se borra nada.

Para que se haga sola todos los días:

    .\tasks.ps1 schedule-backup -At 02:30

- Crea en el Programador de tareas de Windows la tarea **"Diagnostico academico - respaldo diario"**, que ejecuta `backup-daily` con tu usuario (así tiene `APP_MASTER_KEY`, que debe estar en las variables de entorno de tu usuario).
- Si el equipo estaba apagado a esa hora, se ejecuta al encenderlo. Si falla (por ejemplo, Laragon/MySQL apagado), reintenta cada hora, hasta 6 veces.
- El resultado de cada ejecución queda en `%USERPROFILE%\respaldos\respaldo-diario.log`.
- Para comprobarla: Programador de tareas → *Diagnostico academico - respaldo diario* → *Ejecutar*, y revisa el log.
- Para quitarla: `.\tasks.ps1 unschedule-backup`.

### Vaciar la base para empezar desde cero

    .\tasks.ps1 reset

Sirve para mostrar el recorrido completo desde una base vacía (por ejemplo, en una demostración).

1. Hace una copia `antes-vaciar`; **si la copia falla, no borra nada**.
2. Pide escribir el nombre de la base (`excel_reader`) para confirmar; si no coincide, no hace nada.
3. Borra todos los datos académicos: importaciones de Excel (ESE y CORHUILA), resultados, estudiantes y sus correos, programas, TD PROGRAMAS, cursos e inscripciones. Los contadores de id vuelven a 1.
4. Conserva las tablas, las migraciones aplicadas, el estado del dashboard y las **cuentas de usuario**, para poder iniciar sesión y empezar por "Importar Excel".
5. **Reinicia la API** (`.\tasks.ps1 run`): guarda en memoria los datos de las importaciones.

Con `.\tasks.ps1 reset -IncludeUsers` también se borran las cuentas y sesiones; después crea el superadmin con `.\tasks.ps1 bootstrap`.

Para deshacer el vaciado, restaura la copia `…_antes-vaciar.sql`.


## Pruebas

```powershell
.\tasks.ps1 test
```

58 pruebas en SQLite en memoria; no necesitan `core/.env` ni MySQL. Más detalle en [Pruebas y desarrollo](07-pruebas-y-desarrollo.md).

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `core\.env tiene credenciales cifradas. Define APP_MASTER_KEY…` | Falta la clave en esta terminal: `$env:APP_MASTER_KEY = "<clave>"`. |
| `Falta core\.env…` | Copia la plantilla: `Copy-Item core\.env.example core\.env` y complétala. |
| `No existe el venv…` | Ejecuta `.\tasks.ps1 install`. |
| PowerShell no deja ejecutar `tasks.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `/health` responde pero las rutas con base de datos dan `500` | Credenciales o clave incorrectas, o MySQL no accesible. Revisa la terminal de Uvicorn: el error de configuración aparece en la primera petición que usa la base. |
| Error de migración por esquema "incompleto" o "no coincide" | Base antigua sin historial Alembic que no coincide con los modelos. No la fuerces: respáldala y revísala (ver [Seguridad y migraciones](06-seguridad-y-migraciones.md)). |
| La importación responde `409` | Ese mismo archivo ya fue importado y luego desactivado (restáuralo desde **Importaciones**, solo superadmin), o falló. Cualquier cambio en el contenido genera una importación nueva. |
| La importación responde `422` | Faltan las hojas `BD GEN`/`TD PROGRAMAS`, columnas requeridas o la fila `AÑO` de `TD PROGRAMAS`. El mensaje indica cuál. |
| El puerto 8000 está ocupado | `.\tasks.ps1 run -Port 8001` y ajusta `API_BASE_URL` en el frontend. |
| No aparece la copia diaria de un día | Si no hubo cambios, no se crea (es lo esperado). Si no, revisa `%USERPROFILE%\respaldos\respaldo-diario.log`: lo más común es que Laragon/MySQL estuviera apagado durante los 6 reintentos. |
| La API sigue mostrando datos después de `reset` | Guarda las importaciones en memoria: reiníciala con `.\tasks.ps1 run`. |
