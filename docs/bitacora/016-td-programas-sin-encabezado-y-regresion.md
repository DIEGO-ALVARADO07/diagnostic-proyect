# 016 · TD PROGRAMAS sin encabezado y verificación de regresión de la fase 4

- **Fase:** 4
- **Fecha:** 2026-11-22

## Problema (detectado en la entrada 008)

`fastexcel` tomaba la **primera fila** de `TD PROGRAMAS` como nombres de columna. En `CORHUILA.xlsm` esa fila es un título decorativo y no pasaba nada. Pero si un libro empieza directamente con la fila `AÑO`, esa fila se pierde y la importación falla con *"No se encontró el año seleccionado de 'TD PROGRAMAS'"*.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `modules/excel/repositories/dashboard_repository.py` | `load_sheet("TD PROGRAMAS", header_row=None)`, de modo que todas las filas son datos. La numeración empieza en 1, así que `source_row_number` sigue siendo el número de fila real del Excel. |
| `tests/test_dashboard.py` | El test de lectura espera 5 filas en vez de 4 (ahora incluye la de título). Nuevo test `test_td_programas_may_start_directly_with_year_row` con un libro sin fila de título. `make_dashboard_workbook` acepta `td_title_row`. |

El test nuevo **falla con el lector anterior**, con exactamente ese error. Lo comprobé restaurando temporalmente el archivo de `HEAD`. Con el cambio, pasa.

## Verificación de regresión de toda la fase 4

Antes de empezar se tomó una "foto" del resultado de importar `CORHUILA.xlsm` (3.819 filas) en SQLite. La foto se guardó en una carpeta temporal fuera del repositorio, porque contiene datos personales. Incluye:

- la respuesta de la importación, incluida la auditoría;
- 6 overviews con distintos filtros;
- 81 consultas de programa (27 programas × 3 combinaciones de filtro, búsqueda y página);
- 120 historiales de estudiante;
- el listado de importaciones;
- **todas** las filas guardadas en `academic_results`, `td_programas_reference` (también el `source_payload` crudo), `academic_programs` y `academic_students`.

Se comprobó que la foto es determinista: dos ejecuciones dieron el mismo resultado, sin contar ids y fechas. Después de **cada** paso (013, 014, 015 y este) se comparó contra la foto inicial: las 10 secciones son **idénticas**.

## Resultado

- 46 pruebas OK (1 nueva). `pyflakes` sin avisos.
- Benchmark de 20.000 filas: overview ~197 ms, filtrado ~89 ms, programa ~134 ms y estudiante ~7 ms. El costo frente a la fase 3 se explica en la entrada 014.
