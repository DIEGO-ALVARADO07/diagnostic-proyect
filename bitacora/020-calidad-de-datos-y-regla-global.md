# 020 · Reporte de calidad de datos, regla del global y verificación de la fase 5

- **Fase:** 5 (decisiones del 2026-11-22)
- **Fecha:** 2026-11-22

## Decisiones

1. **Regla del global: se mantiene la del Excel.** El global calculado es la suma de las 5 competencias entre 5, con las vacías como 0. Las cifras coinciden con las del archivo institucional. No se cambia código: la regla ya estaba documentada en `dashboard_processor.py` (entrada 014) y ahora también en `IMPLEMENTATION.md`.
2. **Códigos `N` y `P`: se desconoce su significado.** Siguen contando como "sin puntaje", igual que antes, pero ahora se **reportan** para que alguien los revise.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `modules/excel/services/dashboard_data_quality.py` | **Nuevo.** `assess_data_quality(rows)` cuenta, por competencia: `score_codes` (textos no numéricos en el puntaje), `levels_without_numeric_score` (nivel válido sin puntaje numérico) y `unknown_levels` (niveles que no son válidos ni un código conocido). |
| `modules/excel/services/dashboard_processor.py` | Ejecuta el reporte sobre las filas de BD GEN. |
| `modules/excel/repositories/dashboard_persistence_repository.py` | Guarda el reporte en `excel_imports.validation_summary["data_quality"]`. Es una columna JSON que ya existía, así que no requiere migración. |
| `modules/excel/dtos/responses/dashboard.py` | Nuevo `DashboardDataQualityResponse`. `DashboardSourceAuditResponse.data_quality` es opcional: vale `null` en importaciones anteriores. **El cambio es compatible:** solo se añade un campo. |
| `modules/excel/services/dashboard_dataset_loader.py`, `dashboard_audit.py` | Leen el reporte y lo incluyen en `source_audit`. |

## Resultado con `CORHUILA.xlsm`

```json
{
  "score_codes": {"comunicacion_escrita": {"N": 254, "N/A": 489, "P": 12}},
  "levels_without_numeric_score": {"comunicacion_escrita": 60},
  "unknown_levels": {"ingles": {"false": 2}}
}
```

Coincide con lo encontrado en el análisis manual del libro. Las 60 filas son las que tienen puntaje `N` y nivel `4`.

## Pruebas nuevas (`tests/test_dashboard_rules.py`, 11)

- Regla del nombre de programa: gana TD PROGRAMAS; si no hay, la variante con tildes y luego la más frecuente; espacios y mayúsculas no crean programas nuevos.
- `canonical_semester`: casos que se convierten y casos que se conservan.
- Reporte de calidad: con hallazgos y sin ellos.
- Integración: variantes en un solo programa con alias, reimportación sin alias duplicados, semestre `7` junto a `SEMESTRE 7` (incluido el filtro) y `data_quality` en la respuesta.

Además se actualizaron 2 tests de `test_dashboard.py`. Antes esperaban 3 programas separados y 0 diferencias en la auditoría. Ahora hay 1 programa y **1 diferencia real** en los datos de prueba: el GLOBAL de BD GEN (90) no coincide con el GL de TD (120), una discrepancia que antes quedaba oculta por la separación.

## Verificación con el Excel real (fase 4 → fase 5)

| Aspecto | Resultado |
|---|---|
| Programas en filtro | 27 → 17 |
| Semestres en filtro | 9 → 7 |
| Años, simulacros, grupos, tipos y "presentado" | Iguales |
| KPIs globales | Iguales |
| Presentaciones por programa unificado | = suma de sus variantes |
| Auditoría | 48 filas, 328 métricas, 14 diferencias: **mismos valores** |
| Historiales de estudiantes | Mismos intentos y puntajes |
| `academic_results` | Solo cambian `program_id` (ids nuevos) y `semester_key` (498 filas) |
| Estudiantes y TD PROGRAMAS guardados | Iguales |

**Total:** 58 pruebas OK (11 nuevas, más 1 de migración). `pyflakes` sin avisos.
