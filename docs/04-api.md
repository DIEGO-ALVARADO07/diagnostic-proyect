# API y contratos HTTP

> Actualizado el 27 de noviembre de 2026 (rama `dev`, commit `a914c58`).

La especificación OpenAPI está en `/openapi.json` y Swagger UI en `/docs` mientras la API esté en ejecución. Ahí están todos los campos de cada respuesta; este documento resume qué hace cada ruta y quién puede usarla.

## Convenciones

- Todas las rutas, excepto `POST /auth/login` y `GET /health`, requieren `Authorization: Bearer <access_token>`.
- **Roles:** `superadmin`, `instructor` y `estudiante`. Si el rol no alcanza, la respuesta es `403`; sin sesión o con el token vencido, `401`.
- **Errores:** JSON con `detail` (texto o un objeto con `message`). Los más comunes:

  | Código | Cuándo |
  |---|---|
  | `404` | No existe. |
  | `409` | Conflicto: duplicado o elemento eliminado. |
  | `413` | Archivo de más de 30 MB. |
  | `415` | Tipo de archivo no válido. |
  | `422` | Datos inválidos. |

- **Periodo:** `AAAA-1` o `AAAA-2`, por ejemplo `2026-2`. Algunas rutas aceptan además `all` (todo el histórico).
- **Materias** (las 4 competencias comunes): `lectura_critica`, `competencias_ciudadanas`, `razonamiento_cuantitativo` e `ingles`.
- **Programa:** `program_id` es el id numérico como texto, o `sin-programa` para los estudiantes sin programa.

## Autenticación

| Método y ruta | Función |
|---|---|
| `POST /auth/login` | Body `{"username", "password"}`. Devuelve `access_token`, `token_type`, `expires_in` (segundos) y el perfil. El token dura **8 horas**. Una credencial incorrecta da `401`. |
| `POST /auth/logout` | Revoca el token actual (`204`). |

## Usuarios

| Método y ruta | Función | Acceso |
|---|---|---|
| `GET /users/me` | Perfil propio. | Cualquier usuario. |
| `PATCH /users/me` | Cambiar el correo, el nombre o la contraseña propia. | Cualquier usuario. |
| `GET /users` | Cuentas activas (`offset`, `limit` ≤ 100). | Instructor y superadmin. |
| `POST /users` | Crear instructor o estudiante. | Superadmin. |
| `GET /users/{user_id}` | Consultar un perfil. | Según rol; el estudiante solo ve el propio. |
| `PATCH /users/{user_id}` | Actualizar un perfil. | Según rol y cuenta objetivo. |
| `DELETE /users/{user_id}` | Desactivar la cuenta y revocar sus tokens. | Superadmin. |

Las contraseñas requieren al menos 12 caracteres. Las respuestas nunca incluyen `password` ni `password_hash`. No hay registro público, y el superadmin solo se crea con `tasks.ps1 bootstrap`.

## Lectura simple de Excel

`POST /excel/read` (instructor y superadmin) recibe `multipart/form-data` con:
- `file`: `.xlsx`, `.xlsm`, `.xls` u `.ods`, de hasta 30 MB;
- `sheet_name`, opcional: si falta, lee la primera hoja.

Devuelve las filas como JSON **sin guardar nada**.

## Importación y consulta de resultados

Rutas de instructor y superadmin, salvo donde se indica.

| Método y ruta | Función |
|---|---|
| `POST /excel/dashboard/import` | `multipart/form-data` con `file`, `source` (`ESE` o `CORHUILA`) y `period` (`AAAA-S`), los tres obligatorios. **ESE:** libro con las hojas `BD GEN` y `TD PROGRAMAS`; trae todo el histórico. **CORHUILA:** hoja `Calificaciones` exportada de Moodle; es un archivo por periodo. La nueva importación pasa a ser la activa de su espacio (ESE, o CORHUILA de ese periodo) y la anterior queda histórica. Si el mismo archivo (SHA-256) ya estaba importado, devuelve esa importación; si estaba desactivado, responde `409` y pide restaurarlo. |
| `GET /excel/dashboard/active?source=&period=` | Importación activa de ESE (por defecto) o de CORHUILA en un periodo, con filtros, resumen y auditoría. `404` si no hay ninguna. |
| `GET /excel/dashboard/{import_id}` | Resumen del histórico de ESE: indicadores y programas. Filtros: `year`, `period`, `moment` (1–4), `simulation`, `group`, `test_type`, `presented`, `page` y `page_size` (≤ 50). |
| `GET /excel/dashboard/{import_id}/programs/{program_id}` | Métricas de un programa y sus estudiantes paginados (`search`, `page`, `page_size`), con los mismos filtros. |
| `GET /excel/dashboard/{import_id}/students/{document}` | Historial de un estudiante; `document` acepta el documento o el correo. |
| `GET /excel/dashboard/compare?period=&moment=&program_id=` | **Dashboard principal:** ESE y CORHUILA en un periodo (por defecto, el último cargado). Devuelve cada lado (`ese`, `corhuila`; `null` = "a la espera del archivo"), `filters.periods`, `filters.corhuila_periods`, momentos y programas del periodo, el programa con peor nivel y la competencia más baja en común. |
| `GET /excel/dashboard/students` | **Estudiantes por nivel:** todos los de los Excel (ESE y CORHUILA juntos), cada uno con un nivel. Parámetros: `period` (por defecto el último; `all` = histórico), `level` (`1`–`4` o `sin-resultado`), `program_id`, `search`, `page` y `page_size` (≤ 50). Devuelve `groups` (conteo por nivel), `periods`, `programs` y `students`, que trae los niveles por competencia, el promedio y de qué periodo y prueba sale el nivel. |
| `GET /excel/dashboard/program-lookup?document=&email=&full_name=` | Busca en el histórico de ESE a un estudiante y su programa actual (documento → nombre completo → correo). |

**Estados de una importación:**

| Estado | Significado |
|---|---|
| `PROCESSING`, `VALIDATED` | Transitorios, mientras se procesa. |
| `ACTIVE` | La que se consulta en su espacio. |
| `HISTORICAL` | Reemplazada por una más reciente. |
| `FAILED` | La validación falló (`422` al importar). Ningún resultado parcial reemplaza a la activa. |
| `DELETED` | Solo en el listado administrativo, cuando la importación tiene `deleted_at`. |

La respuesta de importación y de `active` incluye `source_audit` con la auditoría frente a `TD PROGRAMAS` y la calidad de datos (`data_quality`). El detalle está en el [flujo del dashboard](09-flujo-dashboard-academico.md).

## Revisión de programas (CORHUILA)

Instructor y superadmin.

| Método y ruta | Función |
|---|---|
| `GET /excel/dashboard/review/without-program?period=` | Estudiantes de CORHUILA "sin programa" (no encontrados en ESE). |
| `GET /excel/dashboard/catalog/programs` | Programas activos para asignar a mano. |
| `PUT /excel/dashboard/review/students/{student_id}/program` | Body `{"program_id": n}` (o `null` para quitarlo). La asignación manual manda sobre ESE. |
| `POST /excel/dashboard/corhuila/resolve` | Vuelve a cruzar todas las filas de CORHUILA con el histórico de ESE. |

## Administración de importaciones (solo superadmin)

| Método y ruta | Función |
|---|---|
| `GET /excel/dashboard/imports?limit=` | Importaciones no desactivadas. |
| `GET /excel/dashboard/admin/imports?limit=` | Historial completo; las desactivadas aparecen como `DELETED`, con `deleted_at`, `deleted_by`, `restored_at` y `restored_by`. |
| `DELETE /excel/dashboard/imports/{import_id}` | Desactivación lógica de una importación `ACTIVE`, `HISTORICAL` o `FAILED`. Guarda quién y cuándo. |
| `POST /excel/dashboard/imports/{import_id}/restore` | Restaura una desactivada. Vuelve a ser la activa si su espacio no tiene otra; si no, queda `HISTORICAL`. Las fallidas siguen fallidas. Devuelve `status`, `activated` y `message`. |

## Cursos

Instructor y superadmin, salvo donde se indica.

| Método y ruta | Función |
|---|---|
| `GET /courses` | Cursos activos agrupados en los 4 niveles. Cada nivel trae `available_students` por materia (cuántos tienen ese nivel en el último periodo), además de `periods` y `competencies`. |
| `POST /courses` | Crea un curso. Body: `name` (3–150), `level` (1–4), `competency`, `description` (10–2000) y `methodology` (10–2000). El nombre no se repite en el mismo nivel y materia: si existe, `409`; si está eliminado, el `409` pide que el administrador lo habilite. |
| `DELETE /courses/{course_id}` | **Eliminación lógica:** conserva el curso y sus inscripciones y guarda quién y cuándo. Devuelve el curso. |
| `GET /courses/{course_id}/students` | Inscritos, con documento, correo, programa, nivel y periodo al inscribirse, y nivel actual en la materia. También funciona con un curso eliminado (auditoría). |
| `POST /courses/{course_id}/enroll` | Body `{"period": "2026-2" \| "all" \| null}`. Inscribe a **todos los que tienen el nivel del curso en su materia** en ese periodo, sin repetir. Devuelve `added`, `already_enrolled` y `level_students`. `409` si el curso está eliminado. |
| `DELETE /courses/{course_id}/students/{student_id}` | Quita a un estudiante del curso (`204`). |
| `GET /courses/deleted` | **Solo superadmin.** Cursos eliminados con toda su información y auditoría. |
| `POST /courses/{course_id}/restore` | **Solo superadmin.** Habilita un curso eliminado con sus inscripciones y guarda quién y cuándo. |

## Estado

`GET /health` no requiere autenticación ni consulta MySQL. Responde `{"status":"ok"}`, lo que indica que la aplicación atiende, no que la base esté disponible.
