# 025. Fuente, periodo y momento; un activo por espacio

**Fecha:** 25 de noviembre de 2026
**Fase:** 8
**Rama de código:** `dev`

## Qué cambió

1. **Fuente de la prueba** (`modules/excel/entities/assessment.py`, nuevo): enum `Source` con `ESE` y `CORHUILA`. `excel_imports` gana `source` (las existentes quedan `ESE`) y `period` (solo CORHUILA, que manda un archivo por periodo).
2. **Periodo y momento por resultado:** `academic_results` gana `period` (`2026-1`) y `moment` (1–3).
   - El periodo sale de `SIM` (`SIMULACRO 2026-1 MOMENTO 3`).
   - El momento sale de `SIM` y, si no lo trae, de `GRUPO` (`MOMENTO 3`).
3. **Rango de semestres por momento:** M1 = 1–3, M2 = 4–6, CORHUILA = 5–6, M3 = 7 en adelante. Se expone como `semester_range` en el historial del estudiante y en la lista de estudiantes del programa. El semestre exacto solo se muestra si el archivo lo trae.
4. **Un activo por espacio:** la nueva tabla `excel_active_imports` guarda el activo de cada espacio. ESE tiene uno solo (`ESE`), porque cada archivo trae toda la historia. CORHUILA tiene uno por periodo (`CORHUILA:2026-2`). Activar o desactivar un espacio no toca los demás. `excel_dashboard_state` queda solo como fila de bloqueo.
5. **API:**
   - Filtros `period` (`AAAA-1`/`AAAA-2`) y `moment` (1–3) en overview y programa.
   - `filters.periods` y `filters.moments`.
   - `GET /excel/dashboard/active?source=CORHUILA&period=2026-2`. Sin parámetros sigue devolviendo ESE.
   - Los listados de importaciones incluyen `source`, `period` y `active_imports`. `active_import_id` se mantiene (es el de ESE).
6. **Calidad de datos:** el nuevo bloque `data_quality.period_moment` cuenta:
   - filas sin periodo;
   - filas sin momento;
   - filas donde `SIM` y `GRUPO` no coinciden (manda `SIM`);
   - filas donde el periodo no es del año de `AÑO`.
7. **Migración `0005_sources_periods_moments`:** agrega las columnas, crea `excel_active_imports`, copia el activo actual a `ESE`, retira `excel_dashboard_state.active_import_id` y rellena `period`/`moment` de los resultados existentes.

## Por qué

Para que ESE y CORHUILA convivan sin reemplazarse y para tener el filtro **Momento**. Ver [00 · Visión](../00-vision-y-modelo-de-dominio.md) y [11 · Plan](../11-plan-de-refactorizacion.md).

## Decisiones (25/11/2026)

- ESE manda siempre la historia completa más lo nuevo: cada archivo reemplaza al anterior.
- El periodo del año se toma de `SIM`; el momento se toma de `SIM` y se confirma con `GRUPO`.
- Como ESE casi no envía `SEMESTRE` desde 2025, el semestre se trabaja por el rango del momento.
- Se guardaron los bocetos del dashboard en [12 · Diseño de pantallas](../12-diseno-de-pantallas.md), para las fases 11 y 12.

## Cómo aplicarla

Haz copia de seguridad de MySQL y luego ejecuta:

```powershell
.\tasks.ps1 migrate
```

## Verificación

- `python -m unittest discover -s tests`: 78 pruebas OK (antes 66). Las nuevas cubren:
  - lectura de periodo y momento;
  - rangos de semestre;
  - espacios activos;
  - que importar ESE no reemplaza a CORHUILA;
  - que desactivar ESE no toca CORHUILA;
  - los filtros nuevos;
  - el relleno de datos de la migración.
- La cadena de migraciones 0001–0005 sube, coincide con los modelos y baja (SQLite).
- `pyflakes`: sin avisos.
- Libro real de ESE: _(completar al reimportar: `data_quality.period_moment` y periodos/momentos encontrados)_.
