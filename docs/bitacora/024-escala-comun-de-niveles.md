# 024. Escala común de niveles y 4 competencias comparables

**Fecha:** 25 de noviembre de 2026
**Fase:** 7
**Rama de código:** `dev`

## Qué cambió

1. **Una sola escala para todas las competencias** (`modules/excel/entities/competency.py`): Nivel 1 = 0–125, Nivel 2 = 126–156, Nivel 3 = 157–198, Nivel 4 = 199–300. Antes cada competencia tenía sus propios cortes (por ejemplo, Razonamiento 125/153/201 e Inglés 120/164/195). Inglés usa los mismos límites y se muestra como A1/A2/B1/B2.
2. **El nivel lo calcula la app** a partir del puntaje (`dashboard_mappers.levels`). El nivel del Excel (Q:U) se sigue guardando, pero solo se usa en la auditoría.
3. **Comunicación escrita sale de la vista y de las métricas** (`Competency.comparable = False`, `COMPARABLE_COMPETENCIES`). Se sigue importando y guardando.
4. **Promedio general con 4 competencias:** `average_general`, `general_standard_deviation` y `simple_competence_average` usan solo las 4 comunes. `average_global` (columna J) no cambia.
5. **Auditoría de TD PROGRAMAS** (`dashboard_audit.py`): sigue comparando con las 5 competencias, porque esa tabla es del propio Excel de ESE.
6. **Calidad de datos:** el nuevo `source_level_mismatches` cuenta, por competencia comparable, las filas donde el nivel del Excel no coincide con el calculado.
7. **Frontend** (`dashboard.js`): muestra "Nivel 1…4" o "A1…B2" según la competencia.

## Por qué

Para comparar ESE y CORHUILA con la misma regla. Ver [00 · Visión y modelo de dominio](../00-vision-y-modelo-de-dominio.md), sección 3.

## Efectos visibles

- Las distribuciones por nivel de ESE cambian en Lectura crítica (corte 124 → 125), Razonamiento cuantitativo (153/201 → 156/198) e Inglés (120/164/195 → 125/156/198).
- El promedio general de las tarjetas ya no incluye Comunicación escrita, así que **deja de coincidir con Power BI** (bitácora 022). El orden de los programas puede cambiar.
- No hay migración: los niveles y promedios se calculan en memoria.

## Verificación

- `python -m unittest discover -s tests`: 66 pruebas OK (antes 61). Las nuevas cubren límites de la escala, inglés A1–B2, exclusión de escritura, la regla "0 cuenta / vacío no cuenta" y `source_level_mismatches`.
- `pyflakes`: sin avisos.
- Libro real de ESE: _(completar al reimportar: `source_level_mismatches` por competencia y nuevos promedios generales de los programas)_.
