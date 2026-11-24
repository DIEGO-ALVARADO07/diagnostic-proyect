# Plan de refactorización: ESE + CORHUILA

> Creado el 24 de noviembre de 2026. Aplica lo definido en [Visión y modelo de dominio](00-vision-y-modelo-de-dominio.md) sobre el código de la rama `dev` (commit `3503800`). Cada fase deja la aplicación funcionando y se registra en la [bitácora](bitacora/README.md).

## Punto de partida

El backend actual ya resuelve bien la prueba **ESE**: importación con snapshots, caché, auditoría, normalización de programas y semestres, y 61 pruebas. Pero supone **una sola fuente** y **un único snapshot activo**.

| Supuesto actual | Lo que se necesita |
|---|---|
| Una sola fuente (archivo con `BD GEN` + `TD PROGRAMAS`) | Dos fuentes: ESE y CORHUILA |
| Un solo snapshot activo (`excel_dashboard_state` con una fila) | Uno activo por **fuente + periodo** |
| 5 competencias con umbrales distintos por competencia | 4 competencias comparables y **una sola escala** (125 / 156 / 198 / 300) |
| Niveles leídos del Excel (Q:U) | Niveles **calculados** por la app. Los de Q:U quedan solo como auditoría |
| Estudiante identificado por documento | Estudiante identificado por **correo** |
| Filtros: año, simulacro, grupo, semestre, tipo | Dashboard: **año, momento, programa**. Módulo de niveles: además semestre, competencia, nivel |
| "Estudiantes" = cuentas de usuario | "Estudiantes" = resultados académicos por nivel |

## Fases

### Fase 7: escala común y competencias

**Objetivo:** que ESE ya hable el lenguaje común, sin cambiar todavía la estructura de datos.

- `modules/excel/entities/competency.py`
  - Una sola tabla de umbrales: `(1, 125), (2, 156), (3, 198), (4, 300)`.
  - Inglés con los mismos límites y etiquetas `A1`–`B2` solo de presentación.
  - Marcar Comunicación escrita como `comparable=False`: se importa, pero no se muestra ni se compara.
- `services/dashboard_metrics.py`: métricas y distribución solo sobre competencias comparables, con niveles 1–4.
- `services/dashboard_data_quality.py`: reportar diferencias entre el nivel de Q:U y el nivel calculado.
- Pruebas: límites exactos (125/126, 156/157, 198/199), `0` cuenta, `-` no cuenta, inglés con los mismos límites.
- **Validación:** volver a importar el libro de ESE y documentar cuánto cambian las distribuciones al pasar a la escala única.

### Fase 8: fuente, periodo y momento en el modelo de datos

- Migración `0005_sources_periods`:
  - `excel_imports`: `source` (`ESE`/`CORHUILA`), `period` (`2026-2`).
  - `academic_results`: `source`, `period`, `moment` (1, 2, 3 o `UNICO`), `level_*` calculados (1–4), `email_key`.
  - `excel_dashboard_state`: pasa de una fila a **una fila por `(source, period)`**.
  - Índices por `(source, period, moment, program_id)`.
- `entities/academic.py`, `entities/import_status.py`, `entities/dashboard.py`: nuevos campos.
- `dashboard_import_service.py` y `dashboard_persistence_repository.py`: activar y desactivar por fuente y periodo.
- ESE: obtener el **periodo** (`AAAA-1`/`AAAA-2`) y el **momento** del archivo. Verificar en el libro real si vienen de `SIM` (por ejemplo `SIMULACRO 2026-2 MOMENTO 1`), de `AÑO` o de `MOMENTO`.
- Migrar los datos existentes como `source = ESE`.
- **Validación:** los resultados de ESE no cambian respecto a la fase 7.

### Fase 9: identidad por correo y vinculación

- `academic_students`: nueva clave `email_key` única. El documento pasa a ser un dato opcional.
- Unificación: un estudiante = un correo, con resultados de ambas fuentes.
- Servicio `program_resolution`: para CORHUILA, toma el programa del registro **ESE Momento 2 más reciente** con el mismo correo. Si no existe, "Sin programa".
- La resolución se recalcula al importar ESE o CORHUILA.
- Auditoría: cantidad de estudiantes CORHUILA sin programa resuelto.

### Fase 10: importación de CORHUILA

- Nuevo `repositories/corhuila_workbook_repository.py`: lee la hoja `Calificaciones` y valida encabezados (`Nombre`, `Apellido(s)`, `Número de ID`, `Dirección de correo`, `Cuestionario:… (Real)`).
- Nuevo `services/corhuila_processor.py`: aplica las reglas comunes (`-` = sin puntaje, `0` cuenta, presentó = al menos un puntaje numérico, semestre 5).
- Periodo: viene en la petición. El frontend lo sugiere desde el nombre (`2026B` → `2026-2`).
- `routes.py`: `POST /excel/dashboard/import` recibe `source` (y `period` para CORHUILA), o se crean dos endpoints. Se mantiene la idempotencia por SHA-256.
- Pruebas con un archivo de muestra anonimizado.

### Fase 11: API comparativa

Nuevos endpoints (instructor y superadmin):

| Endpoint | Devuelve |
|---|---|
| `GET /dashboard/compare?year&moment&program` | Bloque ESE y bloque CORHUILA (cada uno puede venir `null` = "a la espera"); resumen común. |
| `GET /dashboard/{source}?year&moment&program` | Módulo completo de una fuente, con su competencia más débil. |
| `GET /dashboard/{source}/programs/{id}` | Detalle de programa y estudiantes (se reutiliza la consulta actual). |
| `GET /students?search&competency&level&semester&program&source&year` | Lista unificada por nivel. |
| `GET /students/{email}` | Historial del estudiante en ambas pruebas. |

Métricas nuevas en `dashboard_query_service.py` / `dashboard_metrics.py`:

- **Programa con peor nivel promedio:** el promedio de los niveles (1–4) de las 4 competencias de sus estudiantes; el menor valor. Se calcula por fuente y combinado.
- **Competencia más baja en común:** la competencia con menor promedio en ambas fuentes, según los filtros.
- **Competencia más débil por fuente.**

Se quitan los filtros `semester`, `group` y `test_type` del dashboard (siguen disponibles en el módulo de niveles cuando aplique).

### Fase 12: frontend

- `front/partials/report/` (Importar): dos tarjetas de carga, ESE y CORHUILA, con el selector de periodo en CORHUILA.
- `front/partials/dashboard/` (`screen.php`, `data.php`, `dashboard.js`): pantalla dividida, filtros comunes, estado "a la espera del archivo", resumen general abajo. Conviene partir `dashboard.js` (1.116 líneas) en `compare.js`, `source-module.js` y `charts.js`.
- Nuevas vistas `partials/ese/` y `partials/corhuila/`, o una sola vista parametrizada por fuente.
- `front/partials/students/`: se rehace como módulo de **Niveles**.
- `front/partials/imports/`: columna de fuente y periodo.
- `front/index.php`: navegación (Dashboard, ESE, CORHUILA, Niveles, Cursos, Importaciones).

### Fase 13: cursos genéricos

- Migración `0006_courses`: `courses` (competencia, nivel, nombre, descripción, activo) y `course_enrollments` (estudiante, curso, resultado de origen, fecha).
- Se crean los 16 cursos base (4 competencias × 4 niveles).
- Asignación automática al importar: cada estudiante entra al curso de su nivel en cada competencia, según su resultado más reciente.
- API y pantalla de cursos con los filtros del módulo de niveles.

### Fase 6 (pendiente desde antes)

Se mantiene y puede hacerse en paralelo: limpieza de tokens vencidos, cerrar sesiones al cambiar la contraseña, límite de intentos de login, `requirements-dev.txt`, CI, URL de API configurable, CSRF en login y rotación de credenciales de MySQL.

## Orden y dependencias

```text
7 escala ─► 8 fuente/periodo ─► 9 identidad ─► 10 import CORHUILA ─► 11 API comparativa ─► 12 frontend ─► 13 cursos
                                                                            (6 seguridad/CI en paralelo)
```

## Criterios para cerrar cada fase

1. Pruebas automatizadas en verde (`.\tasks.ps1 test`).
2. Libro real de ESE importado: diferencias explicadas en la bitácora.
3. Entrada nueva en la bitácora (qué, dónde, por qué).
4. Documentos afectados actualizados (API, arquitectura, frontend, estado).
