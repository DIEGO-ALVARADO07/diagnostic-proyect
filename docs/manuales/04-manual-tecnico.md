# Manual técnico

**Sistema:** Diagnóstico académico — comparación ESE + CORHUILA
**Para:** desarrolladores y responsables técnicos
**Versión:** 27 de noviembre de 2026 (rama `dev`, commit `a914c58`)

Documentos de referencia:
- [Arquitectura](../02-arquitectura.md), [API](../04-api.md), [Tecnologías y datos](../05-tecnologias-y-datos.md), [Seguridad y migraciones](../06-seguridad-y-migraciones.md), [Pruebas y desarrollo](../07-pruebas-y-desarrollo.md), [Frontend](../08-frontend.md) y [Flujo del dashboard](../09-flujo-dashboard-academico.md);
- la [bitácora](../bitacora/README.md), que explica cada cambio (qué, dónde y por qué).

---

## 1. Visión técnica

El sistema importa dos fuentes de resultados, las normaliza en MySQL y las expone en una API REST que consume un frontend PHP:

| Fuente | Contenido | Hojas |
|---|---|---|
| **ESE** | Libro con todo el histórico de simulacros por momento. | `BD GEN` y `TD PROGRAMAS` |
| **CORHUILA** | Un libro por periodo. | `Calificaciones` de Moodle |

Sobre esos datos, el sistema:
- compara las dos pruebas en un periodo, con una **escala común de niveles**;
- asigna **un nivel por estudiante**;
- arma **cursos por nivel y materia** con inscripción en bloque.

```
Navegador ──► front/ (PHP + JS ES) ──► partials/shared/data.php (proxy, CSRF)
                                          │  Bearer token (sesión PHP)
                                          ▼
                              FastAPI (back/api-reader-excel)
                         security · excel · courses (monolito modular)
                                          │ SQLAlchemy 2
                                          ▼
                                   MySQL 8 (excel_reader)
```

## 2. Tecnologías

| Capa | Tecnología |
|---|---|
| API | Python 3.15, FastAPI 0.162, Uvicorn, Pydantic 2 y pydantic-settings |
| Datos | SQLAlchemy 2.1, Alembic 1.16, PyMySQL y MySQL 8 (Laragon en desarrollo) |
| Lectura de Excel | fastexcel y polars (no ejecuta macros ni guarda el archivo) |
| Seguridad | Hash PBKDF2-SHA256 para las contraseñas, token opaco con hash en la base, y Fernet (`cryptography`) para las credenciales cifradas de `core/.env` |
| Frontend | PHP 7.4+ con cURL; JavaScript con módulos ES nativos, sin compilación; gráficas SVG hechas a mano |
| Operación | PowerShell (`tasks.ps1`), `mysqldump` y el Programador de tareas de Windows |
| Pruebas | `unittest` sobre SQLite en memoria (146 pruebas) |

## 3. Estructura del repositorio

```
diagnostic-proyect/
├── back/api-reader-excel/
│   ├── app/            crea la app FastAPI (logging, errores)
│   ├── api/            ensambla los routers (security, users, excel, courses)
│   ├── core/           config (.env + Fernet), engine, sesión por petición, Base ORM, errores
│   ├── migrations/     Alembic: runner.py y versiones 0001–0011
│   ├── modules/
│   │   ├── security/   login, tokens, usuarios, roles y permisos, bootstrap
│   │   ├── excel/      importación, dashboard, comparación, estudiantes por nivel, revisión
│   │   └── courses/    cursos por nivel y materia e inscripciones
│   ├── scripts/        backup_db.py, reset_db.py, bench_dashboard.py
│   ├── tests/
│   └── tasks.ps1
└── front/              index.php, api_client.php, login/logout, dashboard.css/js, partials/
```

Ramas: **`dev`** (código), **`docs`** (documentación) y `main`.

## 4. Backend

### Capas de cada módulo

| Capa | Qué contiene |
|---|---|
| `routes.py` | HTTP, validación de parámetros y roles con `require_roles(...)`. |
| `services/` | Casos de uso y reglas de negocio. |
| `repositories/` | Acceso a datos y lectura de libros. |
| `entities/` | Modelos ORM y dominio. |
| `dtos/` | Contratos Pydantic de petición y respuesta. Las entidades ORM nunca salen como contrato. |

### Servicios principales de `modules/excel/services`

| Servicio | Responsabilidad |
|---|---|
| `dashboard_service.py` | Fachada que usan las rutas. Compone los demás servicios y comparte la caché. |
| `dashboard_import_service.py` | Importar, desactivar y restaurar. Calcula el hash SHA-256 para no duplicar, activa una importación por espacio y deja `FAILED` las cargas con error. |
| `dashboard_processor.py` y `corhuila_processor.py` | Convierten las hojas de ESE y CORHUILA en registros normalizados. |
| `program_resolution.py` | Cruce de CORHUILA con ESE (documento → nombre completo → correo), programa actual, asignación manual y recálculo. |
| `dashboard_dataset_loader.py` y `dashboard_cache.py` | Cargan la instantánea de una importación y la guardan en memoria; las consultas tardan 5–150 ms. |
| `dashboard_query_service.py` | Resumen, programa y estudiante del histórico de ESE. |
| `dashboard_compare_service.py` | Dashboard principal: ESE frente a CORHUILA en un periodo. |
| `student_levels_service.py` | Un nivel por estudiante. `students_in(db, period)` lo usan Estudiantes y Cursos. |
| `dashboard_metrics.py`, `dashboard_mappers.py` y `dashboard_filters.py` | Métricas, respuestas y opciones de filtros (por ejemplo, `moments_by_period`). |
| `dashboard_audit.py` y `dashboard_data_quality.py` | Auditoría frente a `TD PROGRAMAS` y reporte de calidad de datos. |

### `modules/courses`

`CourseService` se encarga de:
- crear un curso (nivel, materia, nombre, descripción y metodología);
- listarlos por nivel;
- la eliminación lógica, y la restauración solo para el superadmin;
- la inscripción en bloque por el nivel en la materia;
- ver y quitar inscritos.

Reutiliza `StudentLevelsService` y la misma caché del dashboard.

### Entidades del dominio

- `entities/competency.py`: las 5 competencias, con clave, encabezado, columnas y etiquetas de nivel. `COMPARABLE_COMPETENCIES` son las 4 comunes.
- `entities/assessment.py`: `Source` (ESE o CORHUILA), periodo, momento y rango de semestres, `active_slot`, `SIN_PROGRAMA_ID`, `ProgramResolution` y `StudentMatch`.

## 5. Modelo de datos

| Tabla | Contenido |
|---|---|
| `api_users` | Cuentas: rol, hash de la contraseña y estado. |
| `api_access_tokens` | Sesiones: hash del token y vencimiento. |
| `excel_imports` | Cada carga: `source`, `period`, `file_sha256`, estado, conteos, `validation_summary` y auditoría (`deleted_at`, `deleted_by_user_id`, `restored_at`, `restored_by_user_id`). |
| `excel_active_imports` | La activa de cada espacio (`slot`): `ESE` o `CORHUILA:<periodo>`. |
| `excel_dashboard_state` | Fila única que sirve de bloqueo al activar importaciones. |
| `academic_students` | Un estudiante por documento, con su programa manual (`assigned_program_*`). |
| `academic_student_emails` | Los correos de cada estudiante, como alias. |
| `academic_programs` y `academic_program_aliases` | Programas unificados por nombre normalizado, y sus variantes. |
| `academic_results` | Una fila por intento: puntajes y niveles por competencia, global, periodo, momento, simulacro, programa y cómo se resolvió (estudiante y programa). |
| `td_programas_reference` | La tabla visible de `TD PROGRAMAS`, para la auditoría. |
| `courses` | Nivel, `competency`, nombre (y `name_key`, único por nivel y materia), descripción, metodología, autor y auditoría. |
| `course_enrollments` | Curso, estudiante, nivel y periodo de la inscripción, y quién y cuándo. Único por curso y estudiante. |

## 6. Reglas de cálculo

**Escala de niveles.** Se define en `LEVEL_THRESHOLDS`:

| Puntaje | Nivel |
|---|---|
| Hasta 125 | N1 |
| Hasta 156 | N2 |
| Hasta 198 | N3 |
| Más de 198 | N4 |

Inglés usa las etiquetas A1, A2, B1 y B2. El nivel se **calcula** con esta escala; el nivel que trae el Excel solo se usa para la auditoría.

**Comparación.** Solo entran las 4 competencias comunes, sin Comunicación escrita. El promedio general es el promedio conjunto de las competencias con puntaje.

**Nivel del estudiante** (`student_level`):
1. Se toman sus filas del periodo; en el histórico, las de su periodo más reciente con puntajes.
2. Se promedia el puntaje de cada competencia. Si presentó ESE y CORHUILA, entran las dos.
3. Cada promedio se clasifica en la escala.
4. El nivel es el promedio de esos niveles, **redondeado hacia abajo**.

"Sin resultado" significa que no tiene puntajes.

**Cursos.** Se inscribe a los estudiantes cuyo nivel **en la materia del curso** (`competency_levels[materia]`) es igual al nivel del curso.

**Identidad.**
- Un estudiante es el estudiante resuelto; si no hay, su documento; si tampoco, su correo.
- Programa de CORHUILA: el del registro de ESE más reciente, de cualquier momento.
- La asignación manual manda.
- Los no encontrados van a `sin-programa`.

**Periodos de carga.** `periodosDeCarga()`, en `index.php`, solo permite el periodo actual y el anterior; se valida también al recibir el formulario.

## 7. Flujo de importación

1. `POST /excel/dashboard/import` recibe `file`, `source` y `period`. El servicio valida el nombre, el tamaño (30 MB) y la extensión, y calcula el SHA-256. Si el archivo ya existe, devuelve esa importación; si está desactivado, responde `409`.
2. Crea `excel_imports` en `PROCESSING` y lo confirma; el hash único impide cargas simultáneas del mismo archivo.
3. Lee y procesa las hojas, guarda los resultados (`persist_snapshot` o `persist_corhuila_snapshot`) y queda `VALIDATED`.
4. `_activate` bloquea `excel_dashboard_state`. La activa anterior de su espacio pasa a `HISTORICAL` y la nueva queda `ACTIVE`.
5. Un ESE nuevo recalcula el programa de las filas de CORHUILA en la misma transacción.
6. Se limpia la caché de datasets.

Ante cualquier error, la carga queda `FAILED` y no toca a la activa.

## 8. API

La referencia completa por ruta está en [API y contratos](../04-api.md) y en `/docs` (Swagger).

| Grupo | Rutas |
|---|---|
| Autenticación | `/auth/login`, `/auth/logout` |
| Usuarios | `/users`, `/users/me`, `/users/{id}` |
| Lectura simple | `POST /excel/read` |
| Importar y consultar | `/excel/dashboard/import`, `/active`, `/{import_id}`, `/{import_id}/programs/{id}`, `/{import_id}/students/{doc}`, `/compare`, `/students`, `/program-lookup` |
| Revisión de CORHUILA | `/excel/dashboard/review/without-program`, `/catalog/programs`, `PUT /review/students/{id}/program`, `POST /corhuila/resolve` |
| Administración (superadmin) | `/excel/dashboard/imports`, `/admin/imports`, `DELETE /imports/{id}`, `POST /imports/{id}/restore` |
| Cursos | `/courses`, `/courses/{id}/students`, `/courses/{id}/enroll`, `DELETE /courses/{id}`, `DELETE /courses/{id}/students/{sid}`; solo superadmin: `/courses/deleted` y `/courses/{id}/restore` |

## 9. Frontend

Detalle en [Frontend PHP](../08-frontend.md).

- `index.php` arma el menú por rol y carga la pantalla, el CSS y el JS de la vista (`$vistas`).
- Las pantallas con datos tienen `partials/<módulo>/js/main.js`, que llama al proxy `partials/shared/data.php?resource=…`.
  - Las consultas se hacen con `apiRequest`.
  - Los cambios con `apiPost`, que envía el encabezado `X-CSRF-Token`.
- El proxy valida los formatos y los roles (por ejemplo, `courses_deleted` y `course_restore` solo para superadmin) y reenvía a la API con el token.
- Los filtros se guardan en la URL (`history.replaceState`).
- Las confirmaciones usan `window.appConfirm` (`dashboard.js`) o `confirmAction` (`shared/js/confirm.js`).

## 10. Seguridad

| Punto | Cómo está resuelto |
|---|---|
| Credenciales | `core/.env` no se versiona. `DB_USER` y `DB_PASSWORD` pueden ir cifrados con Fernet y se descifran con `APP_MASTER_KEY`. |
| Contraseñas | PBKDF2-SHA256 con sal; al menos 12 caracteres. |
| Tokens | Opacos, de 8 horas. En la base solo se guarda su hash. Se revocan al cerrar sesión por la API y al desactivar la cuenta. |
| Autorización | Siempre en la API (`require_roles`); el menú PHP solo ayuda a la navegación. |
| Frontend | Token en la sesión del servidor, cookie `HttpOnly` y `SameSite=Lax`, y CSRF en los formularios y POST. |
| Auditoría | Eliminación lógica con quién y cuándo en cursos e importaciones; restauración solo del superadmin. |

**Pendiente (fase 6):**
- límite de intentos de login;
- limpieza de tokens vencidos;
- cerrar las sesiones al cambiar la contraseña;
- que `logout.php` revoque el token en la API;
- restringir `/excel/read`;
- integración continua (CI).

## 11. Migraciones

`.\tasks.ps1 migrate` (equivale a `python -m migrations`) valida las bases antiguas sin historial y aplica la cadena `0001`–`0011`. La aplicación **nunca** crea tablas por su cuenta.

| Migración | Qué hace |
|---|---|
| `0001` | Seguridad. |
| `0002` | Esquema académico. |
| `0003` | Desactivación lógica de importaciones. |
| `0004` | Unifica programas. **Fusiona datos.** |
| `0005` | Prueba, periodo y momento. |
| `0006` y `0007` | Identidad por correo, y luego por documento con alias. **Fusionan estudiantes.** |
| `0008` | Programa manual. |
| `0009` | Cursos. |
| `0010` | Auditoría de eliminar y restaurar. |
| `0011` | Materia, descripción y metodología de los cursos. |

Antes de cada migración: `.\tasks.ps1 backup -Label antes-<id>`. La prueba `test_security_migrations` aplica y revierte toda la cadena y la compara con los modelos.

## 12. Pruebas

```powershell
.\tasks.ps1 test
```

146 pruebas en SQLite en memoria; no tocan la base real. Las principales por archivo:

| Archivo | Cubre |
|---|---|
| `test_dashboard*.py` | Importación, métricas, reglas, caché y fuentes. |
| `test_dashboard_compare.py` | Comparación por periodo, momentos y filtros. |
| `test_corhuila_import.py`, `test_student_identity.py`, `test_document_identity.py` | Cruce y estudiantes. |
| `test_student_levels.py` | Niveles y periodos. |
| `test_courses.py` | Cursos, inscripción por materia, eliminar y restaurar, y roles. |
| `test_security_migrations.py` | Cadena de migraciones. |
| `test_backup_db.py`, `test_reset_db.py` | Respaldos y vaciado. |
| `test_auth.py`, `test_config.py`, `test_error_handling.py`, `test_excel.py` | Seguridad, configuración, errores y lectura. |

**Frontend:** `php -l` en las plantillas y `node --check front/dashboard.js`. Para los módulos ES, se comprueba que todos los imports resuelvan.

## 13. Operación (`tasks.ps1`)

| Comando | Qué hace |
|---|---|
| `install` | Crea el venv e instala las dependencias. |
| `migrate` | Aplica las migraciones. |
| `bootstrap` | Migra y crea el superadmin (una sola vez). |
| `run [-Port] [-BindHost]` | Arranca la API. |
| `test` | Corre las pruebas. |
| `backup [-Label]` | Respaldo manual con `mysqldump`; las credenciales van en un archivo temporal de opciones. |
| `backup-daily [-Keep N]` | Respaldo con etiqueta `diario` solo si cambió la huella `CHECKSUM TABLE` (sin `api_access_tokens`). El estado se guarda en `.ultimo-respaldo.json`. |
| `schedule-backup -At HH:mm` | Tarea de Windows con 6 reintentos cada hora y log en UTF-8. |
| `unschedule-backup` | Quita la tarea programada. |
| `reset [-IncludeUsers]` | Respaldo `antes-vaciar`, confirmación con el nombre de la base y vaciado de los datos académicos (`scripts/reset_db.py`). |

## 14. Cómo extender el sistema

1. **Modelo:** crea o extiende un módulo en `modules/<nombre>/` (entities, dtos, service, routes) y registra el router en `api/__init__.py`.
2. **Tablas nuevas:**
   - escribe la migración `00NN_…` en `migrations/versions/`;
   - impórtala en `migrations/env.py`;
   - agrégala a `test_security_migrations`;
   - clasifica la tabla en `scripts/reset_db.py` (se vacía o se conserva). Una prueba falla si falta.
3. **Nuevas rutas protegidas:** usa `require_roles`. Actualiza los conteos en las pruebas de rutas con Bearer (`test_dashboard` y `test_courses`).
4. **Frontend:**
   - agrega la vista en `$vistas` y en el menú de los roles en `index.php`;
   - crea `partials/<vista>/` (`screen.php`, `style.css` y `js/main.js`);
   - agrega los recursos del proxy en `shared/data.php`, con validación y CSRF en los POST.
5. **Confirmaciones:** usa `confirmAction`, nunca `window.confirm`.
6. **Eliminar algo:** siempre de forma lógica, con `deleted_at` y `deleted_by_user_id`, y la restauración solo para el superadmin.
7. **Cada cambio:** pruebas, una entrada en la bitácora (rama `docs`) y la actualización de [Estado y continuidad](../10-estado-y-continuidad.md).

## 15. Pendientes y decisiones abiertas

| Id | Pendiente |
|---|---|
| **13c** | Exportar los estudiantes (por curso o por nivel) a Excel, o hacer una carga masiva, para crearlos en la plataforma oficial de CORHUILA. Por definir. |
| **12c** | Crecimiento por programa (M1 → M2 → CORHUILA → M3); necesita un endpoint nuevo. |
| **Fase 6** | Seguridad y CI (ver sección 10). |
| **Datos** | El nombre de un archivo de CORHUILA guardado con un error de codificación ("Diagnoěstico"), y espacios al final en algunos nombres de simulacro. |
