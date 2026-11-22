# 014 · Competencias en un solo lugar y puntajes por clave

- **Fase:** 4 (modelo de dominio)
- **Fecha:** 2026-11-22

## Problema

Los 5 puntajes y niveles viajaban como **tuplas por posición** (`scores[0]` era lectura crítica, `scores[4]` inglés), y los 7 promedios de TD PROGRAMAS como `averages[0..6]`. El orden se repetía, escrito a mano, en 6 lugares:

- `SCORE_HEADERS` y `LEVEL_HEADERS` en el procesador;
- la lista de encabezados obligatorios del repositorio;
- `COMPETENCIES` en las métricas;
- las asignaciones `reading_score=record.scores[0]…` en la persistencia;
- la carga del dataset;
- la auditoría.

Si alguien reordenaba una lista y no las demás, los puntajes se cruzaban entre competencias **sin ningún error**.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `modules/excel/entities/competency.py` | **Nuevo.** `Competency` reúne, por competencia: clave en la API, nombre, prefijo de columnas en la base (`reading` → `reading_score`, `reading_level`, `reading_average`), encabezado en BD GEN (el del nivel se deriva: `n: …`) y umbrales. También aloja `COMPETENCIES` y `classify_level(competency, score)`. |
| `modules/excel/entities/dashboard.py` | `scores` y `levels` pasan a ser `Mapping[clave → valor]`. `TdProgramasRecord.averages` (7 posiciones) se divide en `competency_averages` (por clave), `global_average` (primera columna GL) y `competency_mean` (segunda columna GL). |
| `modules/excel/services/dashboard_processor.py` | Construye los diccionarios a partir de `COMPETENCIES`. Se eliminan `SCORE_HEADERS` y `LEVEL_HEADERS`. Se documenta en el código que el global calculado sigue la regla del Excel (vacío = 0). |
| `modules/excel/repositories/dashboard_repository.py` | Los encabezados de competencias obligatorios se derivan de `COMPETENCIES`. |
| `modules/excel/repositories/dashboard_persistence_repository.py` | Columnas ORM por nombre (`competency.score_column`, …) en vez de 17 asignaciones por posición. |
| `modules/excel/services/dashboard_metrics.py` | Usa claves. `COMPETENCIES` y `classify_level` se movieron a `entities`. |
| `tests/test_dashboard.py` | `classify_level` recibe la competencia, no un índice. |

## Decisiones

- **No cambia ni el esquema ni la API.** Las columnas siguen siendo `reading_score`, … y las respuestas ya usaban claves (`"lectura_critica": …`).
- `DashboardRecord.scores` y `.levels` son `MappingProxyType`, de solo lectura, porque se comparten vía caché (fase 2).
- **Costo medido:** leer de un `MappingProxyType` es más lento que indexar una tupla. En el benchmark de 20.000 filas, el overview sin filtros pasó de ~172 ms a ~197 ms (medido el mismo día y en la misma máquina, con el commit anterior en una copia temporal del repositorio). Con el Excel real (3.819 filas) son unos pocos ms. Se prefiere la seguridad y la claridad.
