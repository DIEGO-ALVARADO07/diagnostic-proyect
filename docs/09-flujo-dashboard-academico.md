# Flujo completo del dashboard académico

## En una frase

El instructor sube el Excel una vez; la API lee `BD GEN` y la vista guardada de `TD PROGRAMAS`, valida y conserva los intentos en MySQL, activa el snapshot solo cuando la carga termina bien y luego permite consultar primero el resumen global, después cada programa y finalmente el historial de un estudiante.

El backend ya ofrece este flujo. La pantalla PHP todavía no usa estos endpoints: su opción actual de lectura de Excel sigue llamando a `POST /excel/read`, que solo devuelve una vista previa.

En este documento, **snapshot** significa una versión completa e identificable de los resultados importados. Una consulta usa un solo `import_id`, así que no mezcla filas de la carga anterior con las de una carga nueva; la versión anterior permanece disponible como histórica.

## Qué problema resuelve

El libro tiene resultados de varios años y un mismo estudiante puede tener varios intentos. Mandar todas las filas al navegador en cada visita sería pesado y obligaría al frontend a reconstruir relaciones e indicadores. En cambio, la API persiste un snapshot y expone consultas escalonadas:

1. **Global:** indicadores y hasta 50 programas por página.
2. **Programa:** indicadores del programa y hasta 50 intentos/estudiantes por página.
3. **Estudiante:** intentos de ese documento dentro del snapshot.

El navegador nunca se conecta directamente a MySQL; solo consume la API autenticada.

## Antes de usarlo

1. Instala dependencias y configura MySQL siguiendo [Instalación y operación](03-instalacion-y-operacion.md).
2. En una base nueva, ejecuta el bootstrap una sola vez. Este aplica las migraciones existentes antes de crear el primer superadmin.
3. En una base ya utilizada, aplica migraciones pendientes desde `back/api-reader-excel/core` con el entorno virtual y variables de configuración:

   ```powershell
   ..\venv\Scripts\python.exe -m modules.security.migrations
   ```

4. Inicia Uvicorn y abre `http://127.0.0.1:8000/docs` para inspeccionar la API.
5. Inicia sesión con un usuario `instructor` o `superadmin` para obtener un token Bearer.

La migración `0002_academic_dashboard` crea el esquema académico. El servidor no lo crea automáticamente.

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
- Volver a subir un snapshot histórico idéntico no lo vuelve a activar. Para crear una nueva versión, el contenido debe cambiar.

El nombre del archivo no determina la idempotencia; la huella se calcula sobre el contenido.

### 3. Se leen solo las hojas requeridas

- **`BD GEN`:** fuente histórica de intentos individuales.
- **`TD PROGRAMAS`:** tabla dinámica; se conserva el año seleccionado y la referencia visible en el libro al momento de importar.

No se ejecutan macros, no se procesan otras hojas y no se guarda el archivo binario. Si faltan hojas, encabezados requeridos o el año visible de la tabla dinámica, la importación falla con `422`.

### 4. Se conserva el dato de origen

- Cada fila de `BD GEN` es un intento. No se eliminan filas porque repitan estudiante, simulacro o programa.
- La unicidad del intento es `(import_id, source_row_number)`.
- El puntaje GLOBAL principal viene de **J**, sin recalcularlo desde las competencias. Se guarda la representación original y, cuando se puede convertir, también el valor numérico. Un valor no numérico queda `NULL`.
- El cálculo alternativo desde E:I se conserva separado; nunca sustituye el GLOBAL de J.
- Los niveles de origen Q:U se conservan; no se vuelven a inferir desde los puntajes.
- Etiquetas de programa distintas siguen siendo programas distintos. La normalización sirve para comparar/buscar, no para fusionar tildes, espacios o mayúsculas automáticamente.
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
- `source_audit`: año visible de `TD PROGRAMAS`, filas/métricas comparables y diferencias.
- `overview`: indicadores y primera página de programas, limitada a 50.

Los indicadores de puntajes se calculan sobre filas con `APLICA SIMULACRO = Si`; los valores GLOBAL vacíos/no numéricos no entran al promedio. Las diferencias de auditoría se informan, no se corrigen ni bloquean una carga válida.

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

### 3. Consultar el snapshot activo o su historial

```powershell
$active = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/active" `
    -Headers $headers

$imports = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/excel/dashboard/imports?limit=20" `
    -Headers $headers

$imports.active_import_id
$imports.imports | Select-Object import_id, status, filename, bd_gen_row_count
```

### 4. Consultar global, programa y estudiante

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
| `academic_students` | Índice de estudiantes por documento para relacionar sus intentos. |
| `academic_programs` | Catálogo de etiquetas exactas de programa, sin fusiones automáticas. |
| `academic_program_aliases` | Estructura para equivalencias confirmadas; la importación aún no las gestiona ni aplica. |
| `academic_results` | Una fila por intento de `BD GEN`, incluida la fila fuente y los puntajes/niveles. |
| `td_programas_reference` | Valores visibles de la tabla dinámica y año seleccionado en esa importación. |

El archivo original y sus macros no se conservan. Como las filas persistidas incluyen datos personales, la base, sus respaldos y sus credenciales deben protegerse según las políticas de la institución.

## Lo que todavía no hace

- No conecta la pantalla PHP de inicio con estos endpoints. Su reporte actual usa `/excel/read`, que sigue siendo solo lectura/previsualización.
- No recomienda ni asigna cursos automáticamente.
- No recalcula la tabla dinámica guardada; la usa como referencia para auditoría y obtiene historia desde `BD GEN`.

