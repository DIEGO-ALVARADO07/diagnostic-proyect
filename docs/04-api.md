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

## Estado

### `GET /health`

No requiere autenticación ni consulta MySQL. Responde `{"status":"ok"}` para indicar que la aplicación atiende peticiones; no garantiza disponibilidad de la base de datos.
