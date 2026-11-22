# API y contratos HTTP

La especificación OpenAPI está disponible en `/openapi.json`; la interfaz Swagger UI se sirve en `/docs` cuando la API está en ejecución.

## Autenticación

### `POST /auth/login`

Request JSON:

```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

Respuesta: `access_token`, `token_type`, `expires_in` en segundos y el perfil público del usuario (`id`, `username`, `email`, `full_name`, `role`, `is_active`). El token dura 8 horas. Una credencial incorrecta produce `401`.

### `POST /auth/logout`

Requiere `Authorization: Bearer <access_token>`. Revoca el token actual y responde `204`.

Todas las rutas siguientes, excepto `/health`, requieren autenticación Bearer.

## Usuarios

| Método y ruta | Función | Acceso |
|---|---|---|
| `GET /users/me` | Consultar perfil propio. | Cualquier usuario autenticado. |
| `PATCH /users/me` | Cambiar correo, nombre o contraseña propia. | Cualquier usuario autenticado. |
| `GET /users` | Listar cuentas activas; acepta `offset` y `limit` (máximo 100). | Instructor y superadmin. |
| `POST /users` | Crear instructor o estudiante. | Solo superadmin. |
| `GET /users/{user_id}` | Consultar perfil. | Según rol; estudiantes solo el propio. |
| `PATCH /users/{user_id}` | Actualizar perfil según permisos. | Según rol y objetivo. |
| `DELETE /users/{user_id}` | Desactivar cuenta y revocar tokens. | Solo superadmin. |

La contraseña al crear o cambiar cuenta requiere al menos 12 caracteres. Las respuestas de usuario no contienen `password` ni `password_hash`. No hay registro público ni endpoint para crear/promover un superadmin.

## Lectura Excel

### `POST /excel/read`

Requiere rol instructor o superadmin. `multipart/form-data`:

- `file`: archivo `.xlsx`, `.xlsm`, `.xls` u `.ods`, hasta 30 MB.
- `sheet_name`: opcional; debe coincidir exactamente con una hoja. Si se omite, se lee la primera.

Ejemplo con `curl.exe` en PowerShell:

```powershell
$filePath = (Resolve-Path "C:\datos\resultados.xlsx").Path
curl.exe --request POST "http://127.0.0.1:8000/excel/read" `
  --header "Authorization: Bearer $token" `
  --form "file=@$filePath" `
  --form "sheet_name=Hoja1"
```

La respuesta contiene:

```json
{
  "filename": "resultados.xlsx",
  "available_sheets": ["Hoja1"],
  "sheet_read": "Hoja1",
  "total_rows": 1,
  "data": [{"columna": "valor"}]
}
```

La hoja inválida responde `422` con las hojas disponibles; archivo no válido `415`; archivo mayor a 30 MB `413`; usuario sin permiso `403`. El endpoint procesa en memoria y no almacena el archivo ni el JSON.

## Dashboard académico persistente

Estas rutas requieren rol `instructor` o `superadmin` y `Authorization: Bearer <access_token>`. A diferencia de `/excel/read`, importan resultados a MySQL. No guardan el Excel binario. El flujo explicado paso a paso está en la [guía del dashboard](09-flujo-dashboard-academico.md).

| Método y ruta | Función |
|---|---|
| `POST /excel/dashboard/import` | Recibe `file` como `multipart/form-data`, valida `BD GEN` y `TD PROGRAMAS`, crea un snapshot y lo activa si todo termina correctamente. Devuelve filtros, auditoría, métricas y la primera página de programas. |
| `GET /excel/dashboard/active` | Devuelve la importación activa con su resumen y primera página. Responde `404` si todavía no hay snapshot activo. |
| `GET /excel/dashboard/imports?limit=20` | Solo superadmin. Lista snapshots no desactivados, incluidos activos, históricos y fallidos. `limit` va de 1 a 100. Incluye `active_import_id`. |
| `GET /excel/dashboard/admin/imports?limit=100` | Solo superadmin. Historial administrativo completo, incluidos los desactivados, que se presentan con estado `DELETED`. |
| `DELETE /excel/dashboard/imports/{import_id}` | Solo superadmin. Desactivación lógica para estados `ACTIVE`, `HISTORICAL` y `FAILED`; no borra el snapshot. |
| `GET /excel/dashboard/{import_id}` | Devuelve filtros, indicadores y programas de un snapshot no desactivado; instructor solo puede consultar el activo, superadmin también los históricos. |
| `GET /excel/dashboard/{import_id}/programs/{program_id}` | Devuelve métricas del programa y estudiantes paginados. |
| `GET /excel/dashboard/{import_id}/students/{document}` | Devuelve los intentos históricos del documento dentro de esa importación. |

`POST /excel/dashboard/import` acepta archivos de hasta 30 MB en las extensiones que permite el servicio Excel. El mismo contenido identificado por SHA-256 no se vuelve a insertar; si ya existe una importación válida no desactivada, la respuesta vuelve a identificarla. Si ese contenido fue desactivado, la API responde `409`; no hay restauración automática. La vista global pagina hasta 50 programas por petición (`page` empieza en 1; `page_size` de 1 a 50).

Los endpoints de programa y vista global aceptan `year`, `simulation`, `group`, `semester`, `test_type` y `presented`; el endpoint de programa también admite `search`, `page` y `page_size`. `program_id` se obtiene de `filters.programs` o de la lista `overview.programs` de la respuesta de importación. Un programa agrupa todas las escrituras de su nombre que solo difieren en tildes, mayúsculas o espacios; el filtro `semester` trata `4` y `SEMESTRE 4` como el mismo valor. En búsquedas y filtros se conserva el identificador de importación para que las consultas lean siempre el mismo snapshot.

El estado persistido de cada carga puede ser `PROCESSING`, `VALIDATED`, `ACTIVE`, `HISTORICAL` o `FAILED`. `PROCESSING`/`VALIDATED` son estados internos transitorios; normalmente la respuesta exitosa será `ACTIVE`. Si la validación del libro falla se responde `422` y la carga queda registrada como `FAILED`; ningún resultado parcial reemplaza el snapshot activo. `DELETED` es un estado que proyecta el listado administrativo cuando `deleted_at` está establecido; no reemplaza el estado almacenado. Al desactivar el snapshot activo, se limpia `active_import_id`. Los endpoints normales ocultan snapshots desactivados y responden `404` al consultarlos por ID.

### Auditoría y calidad de datos

La respuesta de importación (y `GET /excel/dashboard/active`) incluye `source_audit`:

| Campo | Contenido |
|---|---|
| `years_in_bd_gen`, `td_programas_visible_year` | Años de `BD GEN` y año seleccionado en `TD PROGRAMAS`. |
| `compared_program_rows`, `compared_metrics`, `difference_count`, `differences` | Comparación de `TD PROGRAMAS` con lo calculado desde `BD GEN`, emparejando programa y simulacro por nombre normalizado (máximo 100 diferencias detalladas). |
| `records_without_document` | Intentos sin documento. |
| `data_quality` | `score_codes` (textos no numéricos en puntajes, por competencia), `levels_without_numeric_score` y `unknown_levels`. Es `null` en importaciones anteriores al 22/11/2026. |

Ejemplo de `data_quality` con el libro CORHUILA:

```json
{
  "score_codes": {"comunicacion_escrita": {"N": 254, "N/A": 489, "P": 12}},
  "levels_without_numeric_score": {"comunicacion_escrita": 60},
  "unknown_levels": {"ingles": {"false": 2}}
}
```

## Estado

### `GET /health`

No requiere autenticación ni consulta MySQL. Responde `{"status":"ok"}` para indicar que la aplicación atiende peticiones; no garantiza disponibilidad de la base de datos.
