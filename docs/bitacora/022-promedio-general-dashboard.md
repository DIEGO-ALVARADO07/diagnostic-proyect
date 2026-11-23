# Promedio general del dashboard y contraste con Power BI

> Fase 6: métricas del dashboard. Aplicado el 23 de noviembre de 2026 en la rama `dev`; cambios sin commit.

## Problema

El frontend mostraba `average_global`, el promedio de la columna GLOBAL de `BD GEN`. Power BI calculaba su medida apilando las cinco notas de competencia y omitiendo los valores vacíos. Aunque ambas medidas usan el mismo Excel y los mismos intentos, tienen denominadores distintos y por eso sus promedios por programa no coinciden.

## Cambios

### Backend

Archivos: `back/api-reader-excel/modules/excel/services/dashboard_metrics.py`, `modules/excel/dtos/responses/dashboard.py` y `modules/excel/services/dashboard_query_service.py`.

- Se agregó `average_general`, calculado con todas las notas no nulas de las cinco competencias en los registros presentados. Los valores se acumulan dentro del recorrido existente por competencia.
- Se agregó `general_standard_deviation`, desviación muestral (`statistics.stdev`) de esa lista; con menos de dos notas devuelve `None`.
- Los campos existentes `average_global`, `global_standard_deviation` y `simple_competence_average` conservan su semántica. Las desviaciones ya existentes siguen siendo poblacionales.
- El resumen ordena los programas por `average_general`, descendente, con nulos al final y el mismo desempate normalizado.
- El historial por estudiante añade `program_average_general`; una sola respuesta de métricas por grupo alimenta los promedios general y GLOBAL.
- No se modificaron el procesador, las entidades ORM, las migraciones ni la caché: las métricas se calculan en memoria a partir del dataset.

### Frontend

Archivos: `front/partials/dashboard/dashboard.js` y `front/partials/dashboard/screen.php`.

- Las tarjetas, el KPI global, el panel del programa seleccionado y el detalle de programa muestran `average_general`.
- La comparación individual muestra `program_average_general`; la puntuación individual `global_score` continúa usando la columna GLOBAL.
- Se añadió respaldo a `average_global` cuando la respuesta de una API anterior no incluya `average_general`.
- La etiqueta cambió de **Promedio global** a **Promedio general** para estos indicadores. El formato existente conserva hasta dos decimales y evita redondear a enteros.

## Pruebas

Se agregó `back/api-reader-excel/tests/test_dashboard_metrics.py` con `unittest` para verificar:

- `average_global = 70`, `average_general = 700 / 6`, `simple_competence_average = 110` y `general_standard_deviation = statistics.stdev([100, 100, 100, 100, 100, 200])` ante notas faltantes y un registro no presentado.
- `average_general` y su desviación como `None` cuando no hay notas.
- El orden del overview según el promedio general aunque el promedio GLOBAL ordene los dos programas al revés.

La suite completa pasó con 61 pruebas usando `.\venv\Scripts\python.exe -m unittest discover -s tests`. La ejecución de `.\tasks.ps1 test` fue bloqueada por la política de scripts de PowerShell, por lo que se usó directamente el `unittest` del entorno virtual.

## Verificación con el snapshot local

La consulta autenticada del snapshot de `CORHUILA.xlsm` con `SIMULACRO 2026-2 MOMENTO 1` devolvió los valores esperados de `average_general` (redondeados a dos decimales):

| Programa | Promedio general | Promedio GLOBAL conservado |
|---|---:|---:|
| Administración de Empresas Turísticas | 172,60 | 173 |
| Energías Renovables | 152,05 | 152 |
| Inteligencia Artificial | 149,50 | 149,50 |
| Ingeniería de Sistemas | 149,43 | 144 |
| Negocios Internacionales | 142,03 | 136,57 |
| Ingeniería Industrial | 140,61 | 123,80 |
| Financiera y Bursátil | 140,44 | 137,82 |
| Administración Comercial | 138,85 | 126 |
| Mercadeo | 138,21 | 132,06 |
| Software | 136,55 | 129,81 |
| Mecatrónica | 132,78 | 130,62 |
| Veterinaria | 130,21 | 129,78 |
| Ambiental | 123,20 | 123 |
| Agronómica | 99,87 | 100 |

El `average_global` de Sistemas, Negocios e Industrial se mantuvo en `144`, `136,57` y `123,8`, respectivamente, como antes del cambio.
