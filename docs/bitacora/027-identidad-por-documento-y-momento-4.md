# 027. Identidad por documento con correos como alias, búsqueda del programa y Momento 4

**Fecha:** 26 de noviembre de 2026
**Fase:** 9.1 (corrige la fase 9)
**Rama de código:** `dev`

## Por qué

Con la fase 9 se importó el libro real de ESE. `data_quality.identity` mostró **113 documentos con más de un correo**: el mismo estudiante aparece con un correo institucional (`@corhuila.edu.co`) y con uno personal (`@gmail.com`), y a veces con correos institucionales de distintas cohortes. Con el correo como identidad, esas personas quedaban **partidas en dos estudiantes**, lo que rompe su historial y el cruce con CORHUILA.

`period_moment.rows_without_moment` mostró **285 filas** de `SIMULACRO 2024-1 MOMENTO 4`, un momento que el código no reconocía.

## Qué cambió

1. **Identidad por documento** (`_sync_students`):
   - El documento identifica al estudiante.
   - Todos sus correos quedan como **alias** en la nueva tabla `academic_student_emails` (cada correo pertenece a un solo estudiante).
   - El correo principal (`academic_students.email_key`) es el institucional más reciente.
   - Las filas sin documento se identifican por cualquiera de sus correos.
2. **Consulta del estudiante:** con cualquiera de sus correos o con su documento sale el historial completo.
3. **Estudiante y programa de CORHUILA** (`services/program_resolution.py`):
   - Se busca al estudiante en el ESE activo, en orden: **documento → correo (alias) → nombre completo**. El nombre solo vale si coincide con **un solo** estudiante; si coincide con varios, queda `AMBIGUO` y no se asigna.
   - Lo encontrado se **guarda** en la fila de CORHUILA: `student_id` y `student_match` (`DOCUMENTO`, `CORREO`, `NOMBRE`, `AMBIGUO`, `SIN_COINCIDENCIA`).
   - El programa sale del Momento 2 **de ese estudiante**, con la misma regla de periodo de la fase 9.
   - Ya está listo para cuando el archivo de CORHUILA traiga `Número de ID`.
4. **Nuevo endpoint** `GET /excel/dashboard/program-lookup?document=&email=&full_name=&period=` (instructor y superadmin): muestra qué estudiante y qué programa de ESE se asignarían a esos datos y por qué regla. Sirve para verificar casos puntuales.
5. **Momento 4:** se reconoce como momento histórico (semestres 8–10, solo en 2024).
   - Aparece en el filtro de momento cuando hay datos.
   - Se ve en el historial con `semester_range = "8–10"`.
   - Queda fuera del esquema actual (`CURRENT_ESE_MOMENTS = 1, 2, 3`) para la métrica de crecimiento.
6. **Auditoría:** `data_quality.identity.names_with_multiple_documents` cuenta los nombres completos con más de un documento (en CORHUILA esos nombres darían `AMBIGUO`).
7. **Migración `0007_document_identity_email_aliases`:**
   - Rellena `moment = 4`.
   - Crea los alias.
   - **Une a los estudiantes que la 0006 partió por compartir documento.**
   - Elige el correo principal institucional.
   - Deja de exigir que el correo principal sea único (la unicidad pasa a los alias).
   - Agrega `student_match`.

## Decisiones (26/11/2026)

- El ingeniero ajustará la exportación de CORHUILA para que `Número de ID` llegue siempre. Mientras tanto, el cruce queda listo con documento, correo y nombre completo como respaldo.
- Momento 4 = semestres 8–10, solo en 2024. Desde 2025 el máximo es el Momento 3.

## Cómo aplicarla

Haz copia de seguridad de MySQL: la `0007` une estudiantes y su vuelta atrás no los separa. Luego ejecuta:

```powershell
.\tasks.ps1 migrate
```

## Incidente al aplicarla (26/11/2026)

El primer identificador de la revisión (`0007_document_identity_email_aliases`, 36 caracteres) no cabía en `alembic_version.version_num` (`VARCHAR(32)`). En MySQL cada cambio de estructura se confirma solo, así que la migración se aplicó completa, pero la versión quedó en `0006`.

- Se cambió el identificador a `0007_document_identity`.
- Se comprobó en la base que la migración estaba aplicada y se marcó la versión a mano.
- Se agregó la prueba `test_revision_ids_fit_alembic_version_column` para que ningún identificador vuelva a pasar de 32 caracteres.

## Verificación

- `python -m unittest discover -s tests`: 95 pruebas OK (antes 87). Las nuevas cubren:
  - un estudiante por documento con sus correos como alias;
  - consulta por cualquier correo;
  - reimportación sin duplicados;
  - cruce de CORHUILA por documento, correo, nombre, ambiguo y sin coincidencia;
  - el endpoint de consulta;
  - el Momento 4;
  - la migración 0007.
- La cadena de migraciones 0001–0007 sube, coincide con los modelos y baja (SQLite).
- `pyflakes`: sin avisos.
- Libro real de ESE: _(completar al reimportar: `identity` y `period_moment.rows_without_moment`, que debería quedar en 0)_.
