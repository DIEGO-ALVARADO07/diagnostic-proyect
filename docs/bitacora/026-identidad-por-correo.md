# 026. Identidad del estudiante por correo y programa de CORHUILA desde ESE

**Fecha:** 25 de noviembre de 2026
**Fase:** 9
**Rama de código:** `dev`

## Qué cambió

1. **El correo es la identidad del estudiante.** `academic_students.email_key` guarda el correo en minúsculas y sin espacios (`dashboard_normalizer.email_key`). Es único. `document_key` y `document_number` pasan a ser opcionales, porque CORHUILA casi nunca trae documento.
2. **Al importar** (`DashboardPersistenceRepository._sync_students`):
   - Con correo: el estudiante se busca por correo. Si no existe, se adopta el estudiante de ese documento que aún no tenga correo (datos anteriores a esta fase) o se crea uno nuevo.
   - Sin correo: se busca o se crea por documento.
   - Un documento pertenece a un solo estudiante. Si aparece con otro correo, no se mueve; el caso se reporta en la auditoría.
3. **`academic_results.email_key`:** cada fila guarda su correo normalizado. Un índice nuevo `(import_id, email_key, moment)` acelera el cruce con ESE Momento 2.
4. **Programa de CORHUILA** (`services/program_resolution.py`, nuevo):
   - Se busca el correo en el ESE activo, en filas de **Momento 2** con periodo **igual o anterior** al de CORHUILA, y se usa la más reciente.
   - Si no hay ninguna, la fila queda `SIN_PROGRAMA`.
   - **El resultado se guarda** en la fila de CORHUILA: `program_id`, `program_resolution` (`ESE_M2` / `SIN_PROGRAMA`), `program_resolved_import_id` y `program_resolved_period`. Así el dashboard no repite el cruce en cada consulta.
   - Se recalcula al **activar un ESE nuevo**, en la misma transacción, porque ahí pueden aparecer correos que antes no estaban. La fase 10 lo usará también al importar CORHUILA.
5. **Consultas:**
   - `GET …/students/{documento}` acepta también el **correo**.
   - La búsqueda del programa encuentra por nombre, documento o correo.
   - `document` puede venir vacío en la ficha si el estudiante solo tiene correo.
6. **Auditoría:** el nuevo bloque `data_quality.identity` cuenta:
   - filas sin correo;
   - correos con más de un documento (manda el correo: queda un solo estudiante);
   - documentos con más de un correo (quedan como estudiantes separados).
7. **Migración `0006_student_identity_by_email`:**
   - Agrega las columnas.
   - **Une los estudiantes que comparten correo:** queda el de menor id y sus resultados apuntan a él. No se borra ningún resultado.
   - Rellena `email_key` en los resultados existentes.

## Decisiones (25/11/2026)

- Vale el Momento 2 más reciente con periodo igual o anterior al de CORHUILA.
- Sin Momento 2, la fila queda "Sin programa" (se reporta y se puede revisar).
- Si un correo tiene documentos distintos, manda el correo.
- El programa encontrado se guarda; no se calcula en cada consulta.

## Cómo aplicarla

Haz copia de seguridad de MySQL: la `0006` une estudiantes y su vuelta atrás no los separa. Luego ejecuta:

```powershell
.\tasks.ps1 migrate
```

## Verificación

- `python -m unittest discover -s tests`: 87 pruebas OK (antes 78). Las nuevas cubren:
  - normalización del correo;
  - conteos de identidad;
  - un estudiante por correo en importaciones repetidas;
  - consulta por correo o por documento;
  - adopción de estudiantes antiguos sin correo;
  - elección del Momento 2;
  - programa de CORHUILA guardado al importar ESE;
  - la unión de estudiantes en la migración.
- La cadena de migraciones 0001–0006 sube, coincide con los modelos y baja (SQLite).
- `pyflakes`: sin avisos.
- Libro real de ESE: _(completar al reimportar: `data_quality.identity`)_.
