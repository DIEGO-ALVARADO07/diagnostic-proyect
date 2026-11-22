# 017 · Unificación de programas por nombre normalizado

- **Fase:** 5 (reglas de datos, decisión del 2026-11-22)
- **Fecha:** 2026-11-22

## Decisión

Los nombres que solo difieren en tildes, mayúsculas o espacios son **el mismo programa**.

## Problema

Cada programa se identificaba por el hash de su nombre tal cual venía en el Excel. En `CORHUILA.xlsm` hay **27 escrituras de 17 programas** (por ejemplo, `INGENIERIA DE SISTEMAS` con 387 filas e `INGENIERÍA DE SISTEMAS` con 143, incluso dentro del mismo año). El dashboard partía las métricas de un mismo programa en 2 o 3 filas.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `modules/excel/services/program_catalog.py` | **Nuevo.** `choose_program_names()` elige el nombre visible por clave normalizada, con esta prioridad: 1) el nombre de TD PROGRAMAS (institucional); 2) la variante con más tildes; 3) la más frecuente; 4) orden alfabético, para que sea determinista. |
| `modules/excel/services/dashboard_normalizer.py` | Nuevo `accent_count()`. |
| `modules/excel/services/dashboard_processor.py` | Calcula `program_names` con la regla anterior. Se elimina `program_raw_name_key`. |
| `modules/excel/entities/dashboard.py` | `DashboardImportData` incluye `program_names`. |
| `modules/excel/repositories/dashboard_persistence_repository.py` | Nuevo `_sync_programs()`: un `AcademicProgram` por `normalized_key`, nombre visible actualizado y cada escritura nueva guardada en `academic_program_aliases`. Esa tabla existía desde la migración `0002` pero nadie la usaba. |
| `modules/excel/entities/academic.py` | El índice `ix_academic_programs_normalized_key` pasa a ser **único** (lo crea la migración `0004`, entrada 018). |
| `modules/excel/services/dashboard_dataset_loader.py`, `dashboard_audit.py` | La auditoría empareja TD PROGRAMAS con BD GEN por **nombre normalizado**, no por texto exacto. |
| `modules/excel/services/dashboard_import_service.py` | Después de activar una importación vacía la caché de datasets. El nombre visible de un programa lo comparten todas las importaciones y una caché vieja mostraría el nombre anterior. Es el riesgo que se anotó en la entrada 006. |

## Detalles

- Los alias se comparan en Python, no en SQL, porque la colación por defecto de MySQL ignora tildes y mayúsculas: `INGENIERIA` = `INGENIERÍA`.
- `academic_programs.raw_name_key` se conserva por compatibilidad. En programas nuevos se deriva del hash de la clave normalizada, así que sigue siendo única.
- `academic_results.program_name_raw` sigue guardando el texto original de cada fila.

## Efecto con el Excel real

- El filtro pasa de 27 a **17 programas**, con nombres con tilde: `INGENIERÍA DE SISTEMAS`, `ADMINISTRACIÓN COMERCIAL`, …
- En cada programa unificado, las presentaciones son la suma de las de sus variantes (verificado).
- KPIs globales e historiales de estudiantes: sin cambios.
- La auditoría sigue en 48 filas, 328 métricas comparadas y las mismas 14 diferencias con los mismos valores. Es decir, TD PROGRAMAS ya agrupaba las variantes y ahora la API coincide con ese criterio.
