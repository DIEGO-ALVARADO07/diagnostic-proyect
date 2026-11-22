# 008 · Tests de la caché, benchmark y ajuste de `tasks.ps1 test`

- **Fase:** 2
- **Fecha:** 2026-11-21

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/tests/test_dashboard_cache.py` | **Nuevo.** 10 pruebas: 5 de la LRU (desalojo del menos usado, `invalidate`, `clear`, tamaño 0 y tamaño negativo) y 5 del servicio. |
| `back/api-reader-excel/scripts/bench_dashboard.py` | **Nuevo.** Genera un libro sintético con N filas, lo importa en SQLite en memoria y mide 5 repeticiones de cada consulta. |
| `back/api-reader-excel/tasks.ps1` | La tarea `test` define `LOG_LEVEL=WARNING` si no está definido. Desde la entrada 003, los logs `INFO` de la app se mezclaban con el reporte de `unittest`. |

Las 5 pruebas del servicio verifican que:

- la importación precarga la caché y las consultas siguientes no vuelven a la base de datos;
- tras vaciar la caché, la base de datos se consulta una sola vez;
- `delete_import` desaloja la entrada y la importación responde 404;
- una caché desactualizada, que simula otro proceso de Uvicorn, **no** sirve una importación desactivada;
- el dataset en caché es de solo lectura.

## Resultados del benchmark

20.000 filas y 30 programas, en SQLite en memoria (`scripts/bench_dashboard.py 20000`):

| Consulta | Antes | Con caché (006) | + `normalized_key` (007) |
|---|---:|---:|---:|
| Overview sin filtros | ~1.230 ms | ~212 ms | **~146 ms** |
| Overview filtrado (grupo) | ~1.070 ms | ~159 ms | **~65 ms** |
| Programa | ~1.090 ms | ~171 ms | **~131 ms** |
| Estudiante | ~897 ms | ~10 ms | **~5 ms** |

La primera consulta tras reiniciar el servidor sigue costando lo mismo que antes (~1 s), porque carga desde la base de datos. Las siguientes salen de la caché.

Lo que queda en el overview es el cálculo de métricas (`calculate_metrics`, con `pstdev` por programa y competencia). Si hiciera falta bajar más, el siguiente paso sería cachear las respuestas sin filtros o mover los agregados a SQL. Por ahora no se considera necesario.

## Hallazgo durante el benchmark (sin corregir)

`fastexcel` toma la **primera fila de `TD PROGRAMAS` como encabezado de columnas**. Si el libro real empieza directamente con la fila `AÑO`, esa fila se pierde y la importación falla con "No se encontró el año seleccionado de 'TD PROGRAMAS'". Los tests y el benchmark funcionan porque su primera fila es un título de relleno. Hay que verificarlo con un libro real; si se confirma, se corrige leyendo esa hoja sin encabezado (`header_row=None`) en la fase 4.

## Verificación

- `.\tasks.ps1 test`: 43 pruebas, OK (antes 33).
