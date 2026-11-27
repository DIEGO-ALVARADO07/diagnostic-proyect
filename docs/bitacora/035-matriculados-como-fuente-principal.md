# 035. Matriculados como fuente principal de CORHUILA

**Fecha:** 27 de noviembre de 2026
**Fase:** 14 (14a: módulo Matriculados · 14b: cruce con CORHUILA)
**Rama de código:** `dev` (commit `ac61c9b`)

## Por qué

- El Excel de CORHUILA no trae el **programa**, casi nunca trae el **documento** y no trae el **semestre**. Hasta la fase 13, el programa se buscaba en el histórico de ESE, y quien no aparecía en ESE quedaba "Sin programa".
- La institución entrega en cada periodo el **archivo oficial de matriculados** (por ejemplo, `matriculados_20262_pregrado.xlsx`). Trae, por estudiante y programa:
  - el programa y el semestre actual;
  - el tipo y número de documento y el código;
  - los nombres, los dos correos (personal e institucional), los teléfonos, el género, el estrato y la fecha de nacimiento.
- Decisiones del usuario:
  - Se guardan **todas** las columnas en la base, pero la API y el frontend solo envían lo necesario. Los datos personales solo se ven en el módulo del administrador.
  - Matriculados es la **fuente principal** de CORHUILA: de ahí salen el programa, el documento y el semestre. Más adelante también servirá para crear las cuentas de los estudiantes.
  - **Doble programa:** si un estudiante está en dos programas, el **mismo resultado cuenta en los dos**. La prueba se presenta por estudiante, no por programa. En las listas individuales aparece dos veces, y los dos registros solo difieren en el programa.
  - Sedes y modalidades (`-PITALITO`, Virtual, Híbrida) se toman como vienen.
  - **Solo el superadmin** sube matriculados, para que los docentes no suban archivos distintos. Más adelante se agregarán otros roles.
  - Si una fila de CORHUILA no cumple las condiciones del cruce, queda para revisión. Si la persona no está en matriculados, se usa ESE como antes.

## Qué cambió

### 14a. Módulo Matriculados (solo superadmin)

**Backend: módulo nuevo `modules/enrollment`**

| Archivo | Contenido |
|---|---|
| `entities.py` | `EnrollmentUpload` (una carga por periodo) y `EnrollmentRecord` (una fila por estudiante y programa, con todas las columnas). |
| `service.py` | `EnrollmentService`: lectura, validación, guardado, reemplazo y listado con filtros. |
| `dtos.py` | Respuestas de la carga y del listado (filas, filtros con conteos y cargas por periodo). |
| `routes.py` | `POST /enrollment/import` y `GET /enrollment/records`, los dos solo para el superadmin. |

**Reglas de la carga:**

- **Columnas.** Se reconocen sin importar mayúsculas, tildes, espacios o guiones: `COD_PERIODO`, `COD_PENSUM`, `PROGRAMA`, `SEMESTRE`, `TIP_IDENTIFICACION`, `IDENTIFICACION`, `CODIGO`, `NOMBRES`, `APELLIDOS`, `ESTRATO`, `GENERO`, `FNACIMIENTO`, `TELEFONO`, `MOVIL`, `EMAIL_PERSONAL` y `EMAIL_INSTITUCIONAL`. Son obligatorias `PROGRAMA`, `IDENTIFICACION`, `NOMBRES` y `APELLIDOS`; si falta alguna, la respuesta es `422`.
- **Periodo.** Se elige al subir: el actual o el anterior (`-1` o `-2`). Si el archivo trae `COD_PERIODO` (`20262`), debe coincidir con el elegido; si no coincide, `422`.
- **Una carga activa por periodo.** Al subir otro archivo del mismo periodo, el anterior queda `REPLACED` y se borran sus filas, pero se conserva quién y cuándo lo subió. Si es el mismo archivo (mismo SHA-256) que la carga activa, `409`.
- **Filas.**
  - Sin documento o sin programa: se rechazan y se cuentan.
  - Mismo documento y programa repetidos: se omiten y se cuentan.
  - Mismo documento en dos programas: quedan las dos filas (doble programa).
- **Documento.** Se guarda también `document_key` (SHA-256 del documento), la misma clave de `academic_students`.
- **Al guardar:**
  - se completa el **tipo de documento** de los estudiantes que ya existían;
  - se vuelve a cruzar CORHUILA (14b);
  - se limpia la caché del dashboard.

**Frontend: vista `enrollment` ("Matriculados")**

- Es la **primera opción** del menú del superadmin, porque sin matriculados no se pueden trabajar los demás archivos. Al iniciar sesión se sigue abriendo el Dashboard.
- Tiene un formulario de carga (periodo y archivo, de hasta 30 MB) y tarjetas con las cargas de cada periodo (filas, estudiantes, doble programa, rechazadas, quién y cuándo).
- **Filtros** con conteos: Periodo, Programa, Semestre, Tipo de documento, Género y Estrato. La búsqueda va por nombre, documento, código o correo.
- **Tabla de 11 columnas:** estudiante, documento, programa, semestre, correo institucional, correo personal, teléfono, móvil, género, estrato y fecha de nacimiento. Si el estudiante tiene doble programa, se marca con "N programas". Va de 50 en 50.
- `shared/data.php`: el recurso `enrollment` solo responde al superadmin (`403` para los demás).
- `index.php`: la acción `upload_enrollment` (solo superadmin) y `redirigir()` con parámetros (`http_build_query`).

**Base de datos:** migración `0012_enrollment_records`, con las tablas `enrollment_uploads` y `enrollment_records` y sus índices (periodo y programa, documento y los dos correos).

### 14b. Cruce de CORHUILA con matriculados

**Regla** (`modules/excel/services/program_resolution.py`). Una fila de CORHUILA es de un matriculado **del mismo periodo** si:

1. trae el mismo **documento** (`StudentMatch.DOCUMENTO`), o
2. su **nombre completo** y **uno de sus dos correos** (personal o institucional) coinciden con la **misma** persona (`StudentMatch.MATRICULADOS`). Si coincide solo el nombre o solo el correo, no se cruza.

Si se cruza, la fila toma de matriculados:

- el **programa** (`ProgramResolution.MATRICULADOS`), o los dos si tiene doble programa;
- el **semestre** (`SEMESTRE 5`…);
- el **tipo y número de documento**, que quedan guardados en el estudiante.

Si no se cruza, sigue la regla anterior: el programa de **ESE** y, si tampoco está, **"Sin programa"** (por revisar).

**Prioridad del programa:** `MANUAL` > `MATRICULADOS` > `ESE` > `SIN_PROGRAMA`.

| Archivo | Cambio |
|---|---|
| `program_resolution.py` | `build_enrollment_index`, `match_enrollment`, `ensure_programs` (crea en `academic_programs` los programas de matriculados que no existían) y el estudiante de cada persona (usa el del documento, o le asigna el documento al estudiante actual, o crea uno nuevo). `resolve_results` guarda el programa, el semestre y los programas extra. |
| `entities/academic.py` | `AcademicStudent.document_type` y la tabla nueva `AcademicResultProgram` (`academic_result_programs`): los programas extra de un resultado. |
| `entities/assessment.py` | `ProgramResolution.MATRICULADOS` y `StudentMatch.MATRICULADOS`. |
| `dashboard_dataset_loader.py` | Por cada programa extra se crea una copia del registro: el resultado cuenta en los dos programas del dashboard. Agrega el documento y su tipo al registro. |
| `student_levels_service.py` | En Estudiantes, quien tiene doble programa sale **una vez por programa**, con el mismo nivel; la clave del estudiante lleva el sufijo `-p{program_id}`. |
| `enrollment/service.py` | Al subir matriculados se vuelve a cruzar CORHUILA y la respuesta dice cuántas filas cambiaron (`corhuila_rows_updated`). |

- **El orden de carga no importa:** si CORHUILA se sube primero, el cruce se repite al subir matriculados.
- **Frontend:**
  - Estudiantes muestra el tipo junto al número (`C 1075…`).
  - CORHUILA explica la regla nueva en la lista "Sin programa".
  - El aviso de la carga de matriculados dice cuántos resultados de CORHUILA se actualizaron.
- **Base de datos:** migración `0013_enrollment_matching`, que agrega `academic_students.document_type` y la tabla `academic_result_programs`.
- `scripts/reset_db.py`: `tasks.ps1 reset` vacía también `enrollment_records`, `enrollment_uploads` y `academic_result_programs`.

## Verificación

- **Pruebas:** 160 en total.
  - 9 nuevas en `tests/test_enrollment.py`: lectura, doble programa, filtros, búsqueda, reemplazo, `409`, periodo distinto, columnas faltantes y rutas solo para el superadmin.
  - 5 nuevas en `tests/test_enrollment_matching.py`: CORHUILA antes o después de matriculados, doble programa en los dos programas, reemplazo que quita el programa extra y tipo de documento de los estudiantes de ESE.
- **Archivo real de 2026-2** (solo conteos; los datos son personales y no se copian aquí):
  - 2.274 filas, 2.272 estudiantes, 2 con doble programa y 23 programas (9 se crearon en el catálogo).
  - Tipos de documento: C 1.851, T 420 y uno de E, P y PPT.
- **CORHUILA 2026-2 (439 filas) después del cruce:**

  | Resultado | Filas |
  |---|---|
  | Cruzadas por nombre y correo | 433 |
  | Cruzadas por documento | 4 |
  | Programa de ESE (no cumplieron nombre y correo) | 2 |
  | Sin programa | 0 |

  - 437 filas tienen semestre.
  - Las 2 filas con doble programa cuentan en los dos.
- Antes de `0013` se sacó el respaldo `antes-0013`. La `0012` solo crea tablas nuevas.
