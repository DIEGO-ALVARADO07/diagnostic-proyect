# Flujo completo del dashboard académico

## En una frase

El instructor sube el Excel una vez; la API lee `BD GEN` y la vista guardada de `TD PROGRAMAS`, valida y conserva los intentos en MySQL, activa el snapshot solo cuando la carga termina bien y luego permite consultar primero el resumen global, después cada programa y finalmente el historial de un estudiante.

El frontend PHP importa el libro y consume estos endpoints para representar el dashboard. En el módulo independiente **Importaciones**, solo el superadmin puede revisar todos los estados y desactivar snapshots activos, históricos o fallidos. Al desactivar el activo, el dashboard queda sin datos hasta la siguiente importación.

En este documento, **snapshot** significa una versión completa e identificable de los resultados importados. Una consulta usa un solo `import_id`, así que no mezcla filas de la carga anterior con las de una carga nueva; la versión anterior permanece disponible como histórica.

## Qué problema resuelve

El libro tiene resultados de varios años y un mismo estudiante puede tener varios intentos. Mandar todas las filas al navegador en cada visita sería pesado y obligaría al frontend a reconstruir relaciones e indicadores. En cambio, la API persiste un snapshot y expone consultas escalonadas:

1. **Global:** indicadores y programas filtrados; el endpoint entrega hasta 50 por solicitud y el frontend muestra seis tarjetas por página.
2. **Programa:** indicadores del programa y hasta 50 intentos/estudiantes por página.
3. **Estudiante:** intentos de ese documento dentro del snapshot.

El navegador nunca se conecta directamente a MySQL; solo consume la API autenticada.

En el frontend, el resumen global muestra seis tarjetas de programa por página para mantener nombres y promedios legibles: con los 17 programas actuales son tres páginas. La API entrega hasta 50 programas en esa consulta global; la paginación visual no vuelve a solicitar el resumen al avanzar o retroceder. Por eso el filtro de programa se rellena con los programas que realmente coinciden con el año y simulacro consultados, no con el catálogo completo.

En el detalle de programa, la búsqueda por nombre o documento consulta el siguiente bloque de estudiantes en segundo plano y reemplaza solo las filas de la tabla. No oculta la página ni reinicia el desplazamiento.

## Antes de usarlo

1. Instala dependencias y configura MySQL siguiendo [Instalación y operación](03-instalacion-y-operacion.md).
2. En una base nueva, ejecuta `.\tasks.ps1 bootstrap` una sola vez. Aplica las migraciones antes de crear el primer superadmin.
3. En una base ya utilizada, aplica las migraciones pendientes desde `back/api-reader-excel` (con copia de seguridad antes de `0004`):

   ```powershell
   .\tasks.ps1 migrate
   ```

4. Inicia la API con `.\tasks.ps1 run` y abre `http://127.0.0.1:8000/docs` para inspeccionar la API.
5. Inicia sesión con un usuario `instructor` o `superadmin` para obtener un token Bearer.

La migración `0002_academic_dashboard` crea el esquema académico, `0003_soft_delete_excel_imports` añade la marca de desactivación lógica y `0004_unify_programs` unifica los programas por nombre normalizado. El servidor no crea ni actualiza estas tablas automáticamente.

## Qué pasa al subir el libro

```text
Usuario autenticado
  → POST /excel/dashboard/import
  → comprobación de rol, formato y tamaño
  → registro PROCESSING + huella SHA-256
  → lectura de BD GEN y TD PROGRAMAS
  → normalización de cada fila de origen
  → transacción MySQL: datos + referencias + activación
  → respuesta con auditoría y página global inicial
```

### 1. Se autentica y valida la solicitud

La carga requiere `Authorization: Bearer <token>` y rol `instructor` o `superadmin`. El archivo no puede superar 30 MB y debe tener una extensión admitida por el servicio Excel.

### 2. Se identifica el contenido

La API calcula SHA-256 sobre los bytes recibidos y crea un registro `PROCESSING`. Si ya existe exactamente ese contenido:

- Si su importación terminó bien, devuelve el identificador de esa versión en vez de insertar otra copia.
- Si la importación anterior quedó `FAILED` o sigue `PROCESSING`, responde `409`.
- Si esa importación fue desactivada lógicamente, responde `409`; no hay restauración automática.
- Volver a subir un snapshot histórico idéntico no lo vuelve a activar. Para crear una nueva versión, el contenido debe cambiar.

El nombre del archivo no determina la idempotencia; la huella se calcula sobre el contenido.

### 3. Se leen solo las hojas requeridas

- **`BD GEN`:** fuente histórica de intentos individuales.
- **`TD PROGRAMAS`:** tabla dinámica; se lee sin fila de encabezado y se conserva el año seleccionado y la referencia visible en el libro al momento de importar.

No se ejecutan macros, no se procesan otras hojas y no se guarda el archivo binario. Si faltan hojas, encabezados requeridos o el año visible de la tabla dinámica, la importación falla con `422`.

### 4. Se conserva el dato de origen

- Cada fila de `BD GEN` es un intento. No se eliminan filas porque repitan estudiante, simulacro o programa.
- La unicidad del intento es `(import_id, source_row_number)`.
- El puntaje GLOBAL principal viene de **J**, sin recalcularlo desde las competencias. Se guarda la representación original y, cuando se puede convertir, también el valor numérico. Un valor no numérico queda `NULL`.
- El cálculo alternativo desde E:I se conserva separado; nunca sustituye el GLOBAL de J.
- Los niveles de origen Q:U se conservan; no se vuelven a inferir desde los puntajes.
- Los nombres de programa que solo difieren en tildes, mayúsculas o espacios son el mismo programa (p. ej. `INGENIERIA DE SISTEMAS` e `INGENIERÍA DE SISTEMAS`). Ninguna fila se suma ni se fusiona: solo cambia el programa al que pertenece, y los promedios se calculan sobre todas sus filas. Cada escritura original queda como alias y en `program_name_raw`.
- `4` y `SEMESTRE 4` se tratan como el mismo semestre; se guarda el texto original.
- Los códigos no numéricos en puntajes (`N`, `N/A`, `P`) cuentan como sin puntaje y se informan en la auditoría.
- Las filas sin documento permanecen como intentos. No se cuentan como estudiantes únicos ni se pueden consultar por documento.

### 5. Se guardan los resultados y se cambia la versión activa

La API inserta las entidades relacionales de importación, estudiantes, programas, resultados y referencias de TD en una transacción. Al activarla, la fila de `excel_dashboard_state` coordina el cambio:

- El snapshot que era `ACTIVE` pasa a `HISTORICAL`.
- El nuevo pasa a `ACTIVE`.
- El ID activo cambia en el mismo commit que los datos.

Si hay un error antes del commit, los resultados y referencias parciales se revierten; la importación queda registrada como `FAILED` y el snapshot que ya estaba activo no cambia. Los estados de una importación son `PROCESSING`, `VALIDATED`, `ACTIVE`, `HISTORICAL` o `FAILED`.

### 6. Se responde con el resumen

La respuesta de importación incluye:

- `import_id`, `filename`, `status` e `imported_at`.
- `filters`: años, simulacros, programas y otros filtros encontrados en `BD GEN`.
- `source_audit`: año visible de `TD PROGRAMAS`, filas/métricas comparables, diferencias y `data_quality` (códigos en puntajes y niveles inconsistentes).
- `overview`: indicadores y primera página de programas, limitada a 50.

Los indicadores de puntajes se calculan sobre filas con `APLICA SIMULACRO = Si`; los valores GLOBAL vacíos/no numéricos no entran al promedio. Las diferencias de auditoría se informan, no se corrigen ni bloquean una carga válida.

### Promedio general y comparación con Power BI

Las respuestas de métricas conservan `average_global` y `simple_competence_average` con sus definiciones existentes, y agregan `average_general`:

- `average_global` promedia los valores numéricos de la columna GLOBAL de `BD GEN` (columna J). La regla institucional por fila puede tratar una competencia vacía como cero, por lo que este promedio no equivale a ignorar las competencias ausentes.
- `simple_competence_average` promedia los promedios calculados por separado para cada competencia.
- `average_general` reúne todas las notas no nulas de las cinco competencias de los registros presentados y calcula un solo promedio sobre esa lista. No promedia los cinco promedios; coincide con la medida de Power BI que despivota las competencias e ignora celdas vacías.

El resumen global ordena los programas por `average_general` descendente y deja al final los que no tienen notas. `general_standard_deviation` usa desviación muestral (`STDEV.S`) y requiere al menos dos notas; `global_standard_deviation` y `standard_deviation` por competencia mantienen su desviación poblacional existente. La consulta individual añade `program_average_general` junto a `program_average_global`; los campos individuales `global_score` permanecen sin cambios. Estos valores se calculan en memoria desde el dataset cargado y no requieren una migración ni una invalidación especial de la caché.

## Cómo usarlo desde PowerShell

Los ejemplos suponen que la API corre en `http://127.0.0.1:8000`. Sustituye las credenciales de muestra localmente; no las guardes en scripts ni en Git.

### 1. Obtener token

```powershell
$loginBody = @{
    username = "<usuario-instructor>"
    password = "<contraseña>"
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$token = $login.access_token
$headers = @{ Authorization = "Bearer $token" }
```

### 2. Importar el snapshot

```powershell
$filePath = (Resolve-Path "C:\datos\CORHUILA.xlsm").Path
$importJson = curl.exe --silent --show-error `
    --request POST "http://127.0.0.1:8000/excel/dashboard/import" `
    --header "Authorization: Bearer $token" `
    --form "file=@$filePath"

$import = $importJson | ConvertFrom-Json
$import.import_id
$import.status
$import.overview.kpis
```

Guarda `import_id` para consultar esa misma versión. La importación también devuelve los programas de la primera página.

### 3. Consultar el snapshot activo y listar el historial (solo superadmin)

Para consultar únicamente el snapshot activo se puede usar un instructor o superadmin. La consulta del historial y el paso de desactivación requieren que `$headers` contenga el token de un superadmin.

```powershell
$active = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/active" `
    -Headers $headers

$imports = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/admin/imports?limit=100" `
    -Headers $headers

$imports.active_import_id
$imports.imports | Select-Object import_id, status, filename, bd_gen_row_count
```

El instructor consulta el snapshot activo. Para ejecutar la consulta de historial, inicia sesión con un superadmin: el instructor no puede listar ni abrir snapshots históricos. El endpoint administrativo muestra todos los estados, incluidos los desactivados.

### 4. Desactivar una importación (solo superadmin)

El módulo **Importaciones** del menú de superadmin lista todos los snapshots, incluidos los desactivados. La acción **Desactivar** aplica una eliminación lógica con `deleted_at`: conserva el registro y sus resultados, pero los endpoints normales dejan de incluirlos y responden `404` ante consultas directas. Solo el historial administrativo muestra el estado `DELETED`.

El endpoint `DELETE /excel/dashboard/imports/{import_id}` aplica la misma autorización en el backend. Permite desactivar snapshots `ACTIVE`, `HISTORICAL` o `FAILED` y rechaza los estados `PROCESSING` y `VALIDATED`. Al desactivar el activo, limpia `active_import_id`, por lo que el dashboard queda sin resultados hasta la siguiente importación. No borra el archivo original porque la API no lo almacena.

```powershell
$historicalImportId = "<id-historica-verificada>"
Invoke-RestMethod `
    -Method Delete `
    -Uri "http://127.0.0.1:8000/excel/dashboard/imports/$historicalImportId" `
    -Headers $headers
```

### 5. Consultar global, programa y estudiante

```powershell
$importId = $active.import_id

# Resumen global: 50 programas por página como máximo.
$overview = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/$importId?page=1&page_size=50" `
    -Headers $headers

# Toma un ID devuelto por filters.programs u overview.programs.
$programId = $overview.programs[0].program_id
$program = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/$importId/programs/$programId?page=1&page_size=50&search=ana" `
    -Headers $headers

# Solo los intentos con documento se pueden consultar como estudiante.
$studentRow = $program.students |
    Where-Object { $_.document } |
    Select-Object -First 1
if ($null -eq $studentRow) {
    throw "El programa no tiene estudiantes con documento en esta página."
}
$document = [uri]::EscapeDataString($studentRow.document)
$student = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/$importId/students/$document" `
    -Headers $headers

$student.history
```

Los filtros disponibles son `year`, `simulation`, `group`, `semester`, `test_type` y `presented`; en programa se puede añadir `search`. Usa el mismo `import_id` en todas las consultas para mantenerlas sobre el mismo snapshot aunque posteriormente se importe un libro nuevo.

## Qué significan las tablas

| Tabla | En palabras simples |
|---|---|
| `excel_imports` | Historial de archivos procesados, hash, conteos, usuario, fecha y estado. |
| `excel_dashboard_state` | Una sola fila que indica qué importación se considera activa. |
| `academic_students` | Índice compartido de estudiantes por documento para relacionar sus intentos; se conserva al desactivar un snapshot. |
| `academic_programs` | Un programa por nombre normalizado, con el nombre visible elegido. |
| `academic_program_aliases` | Cada escritura original encontrada de un programa. |
| `academic_results` | Una fila por intento de `BD GEN`, incluida la fila fuente y los puntajes/niveles. |
| `td_programas_reference` | Valores visibles de la tabla dinámica y año seleccionado en esa importación. |

El archivo original y sus macros no se conservan. Como las filas persistidas incluyen datos personales, la base, sus respaldos y sus credenciales deben protegerse según las políticas de la institución.

## Lo que todavía no hace

- No permite desactivar importaciones en estado `PROCESSING` o `VALIDATED`.
- No recomienda ni asigna cursos automáticamente.
- No recalcula la tabla dinámica guardada; la usa como referencia para auditoría y obtiene historia desde `BD GEN`.

