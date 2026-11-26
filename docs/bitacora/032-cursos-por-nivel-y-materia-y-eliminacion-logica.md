# 032. Cursos por nivel y materia, eliminación lógica con auditoría y restauración del administrador

**Fecha:** 26 de noviembre de 2026
**Fase:** 13b
**Rama de código:** `dev` (commit `e813cb9`)

## Cambio de negocio

1. **Estructura Nivel → Curso → Estudiantes.** Instructor y superadmin crean cursos con:
   - **nivel** (1–4);
   - **materia**: una de las 4 evaluadas en las pruebas (Lectura crítica, Competencias ciudadanas, Razonamiento cuantitativo o Inglés);
   - **nombre**, **descripción** y **metodología**.

   Así cada nivel puede tener un curso para cada materia. El nombre no se repite en el mismo nivel y materia (sin importar tildes ni mayúsculas).
2. **Inscripción en bloque por el nivel en la materia.** Lo decidió el usuario. "Agregar estudiantes" inscribe a todos los que, en un periodo, tienen **en la materia del curso** el nivel del curso. El periodo es por defecto el último; también se puede elegir otro o "Todo el histórico".
   - Ejemplo: Inglés de Nivel 1 recibe a los que tienen A1 en Inglés, aunque su nivel general sea otro.
   - Los que ya estaban inscritos no se repiten, y nadie se inscribe a mano.
   - La inscripción guarda el nivel y el periodo de ese momento. La lista del curso muestra además el nivel actual en la materia, por si cambió después.
3. **Nada se borra (auditoría).**
   - **Cursos:** "Eliminar" (instructor y superadmin) marca el curso con quién y cuándo, y conserva sus inscripciones.
   - **Importaciones de Excel:** la desactivación ya era lógica; ahora también guarda quién la hizo.
4. **Solo el administrador restaura.**
   - **Cursos:** el instructor no ve los eliminados ni puede habilitarlos. El superadmin tiene el panel **"Cursos eliminados"**, con una tabla de cada curso eliminado (materia, nivel, descripción, metodología, estudiantes, quién lo creó y quién lo eliminó, con fecha) y el botón **"Habilitar"**. El curso vuelve a su nivel con sus estudiantes y queda registrado quién lo habilitó.
   - **Importaciones:** en Importaciones (solo superadmin), cada importación desactivada tiene **"Restaurar"**. Vuelve a ser la activa si su prueba y periodo no tienen otra; si después se subió una más reciente, queda como histórica. Si se vuelve a subir un archivo desactivado, el mensaje pide restaurarlo.
5. **Importar Excel:** los selects de Prueba y Periodo quedan alineados (misma altura y ancho).

## Qué cambió en el código

**Backend**

- Módulo nuevo **`modules/courses/`**:

  | Archivo | Contenido |
  |---|---|
  | `entities.py` | `Course` (nivel, materia, nombre, descripción, metodología, autor y auditoría de eliminación y restauración) y `CourseEnrollment` (estudiante, nivel y periodo de la inscripción, quién y cuándo). |
  | `service.py` | `CourseService`: listar por nivel, crear, eliminar (lógico), restaurar, listar eliminados, inscribir por nivel en la materia, ver y quitar estudiantes. |
  | `dtos.py` y `routes.py` | DTO y rutas `/courses`. |

- **Endpoints nuevos:**

  | Endpoint | Rol | Para qué |
  |---|---|---|
  | `GET /courses` | instructor, superadmin | Cursos activos en los 4 niveles y estudiantes disponibles por materia. |
  | `POST /courses` | instructor, superadmin | Crear (`name`, `level`, `competency`, `description`, `methodology`). |
  | `DELETE /courses/{id}` | instructor, superadmin | Eliminación lógica. |
  | `GET /courses/{id}/students` | instructor, superadmin | Estudiantes inscritos. |
  | `POST /courses/{id}/enroll` | instructor, superadmin | Inscribir en bloque (`{"period": "2026-2" \| "all" \| null}`). |
  | `DELETE /courses/{id}/students/{student_id}` | instructor, superadmin | Quitar a un estudiante. |
  | `GET /courses/deleted` | superadmin | Cursos eliminados con toda su información. |
  | `POST /courses/{id}/restore` | superadmin | Habilitar un curso eliminado. |
  | `POST /excel/dashboard/imports/{id}/restore` | superadmin | Restaurar una importación desactivada. |

- `student_levels_service.py`: el nuevo `students_in(db, period)` devuelve todos los estudiantes de un periodo. Lo usan Estudiantes y Cursos, así que los dos calculan el nivel igual. Cada estudiante trae ahora `student_id`.
- `dashboard_import_service.py`:
  - `delete_import` guarda quién desactivó;
  - el nuevo `restore_import` reactiva o deja histórica;
  - la lista del administrador trae `deleted_by`, `restored_at` y `restored_by`.
- **Migraciones:**

  | Migración | Qué hace |
  |---|---|
  | `0009_courses` | Tablas `courses` y `course_enrollments`. |
  | `0010_soft_delete_audit` | `courses`: `deleted_at`, `deleted_by_user_id`, `restored_at` y `restored_by_user_id`. `excel_imports`: `deleted_by_user_id`, `restored_at` y `restored_by_user_id`. |
  | `0011_course_details` | `courses`: `competency`, `description` y `methodology`; el nombre único pasa a ser por nivel y materia. |

**Frontend**

- `partials/courses/`:
  - el formulario (nivel, materia, nombre, descripción y metodología);
  - el periodo para inscribir;
  - los 4 niveles desplegables, con los estudiantes disponibles por materia y las tarjetas de curso (Agregar estudiantes, Ver estudiantes con "Quitar", Eliminar).
- `partials/courses_deleted/` (nuevo): el panel del superadmin con la tabla de eliminados y "Habilitar".
- `partials/imports/`: el botón Restaurar y la auditoría bajo el estado.
- `shared/data.php`:
  - recursos `courses`, `course_students` y `courses_deleted` (este solo superadmin);
  - `course_create`, `course_enroll`, `course_delete`, `course_restore` (solo superadmin) y `course_remove_student`, todos con CSRF.
- `index.php`:
  - vistas `courses` y `courses_deleted`, y la acción `restore_excel_import`;
  - en el menú, Cursos para los dos roles, Estudiantes para el superadmin (no lo tenía) y Cursos eliminados solo para el superadmin.
- `report/style.css`: el formulario de carga con columnas iguales, alineado arriba.

## Cómo aplicarla

En cada MySQL que tenga el proyecto:

```powershell
.\tasks.ps1 backup -Label antes-0009
```

```powershell
.\tasks.ps1 migrate
```

`migrate` aplica 0009, 0010 y 0011 en orden. Las tres solo agregan tablas y columnas, y no cambian datos existentes.

## Verificación

- `python -m unittest discover -s tests`: 139 pruebas OK (antes 130). Las nuevas cubren:
  - los 4 niveles con los estudiantes disponibles por materia;
  - crear con materia, descripción y metodología, y rechazar duplicados (el mismo nombre sí vale en otra materia u otro nivel);
  - la inscripción por el nivel en la materia, sin repetir, y desde otro periodo;
  - quitar a un estudiante;
  - la eliminación lógica con auditoría: el curso conserva sus inscripciones, no recibe cambios y no se puede volver a crear;
  - la restauración y la lista de eliminados;
  - que restaurar y ver eliminados sea solo del superadmin, mientras eliminar está permitido al instructor;
  - restaurar una importación (activa si su espacio está libre, histórica si ya hay otra) con su auditoría, y el bloqueo de volver a subir un archivo desactivado;
  - la cadena de migraciones hasta la 0011.
- En el navegador, con el libro real y la cuenta de instructor:
  - Inglés Nivel 1 en 2026-2 recibió 151 estudiantes (los que tienen A1);
  - Nivel 1 muestra 196 / 183 / 220 / 151 estudiantes por materia;
  - eliminar quita el curso de la lista;
  - el instructor no ve "Cursos eliminados", la página no le abre y habilitar le responde 403.
  - Los cursos de prueba se borraron después directamente en MySQL.
- La tabla de "Cursos eliminados" del superadmin se verificó desde la API (trae toda la información del curso). En pantalla la revisó el usuario con su cuenta de administrador.
