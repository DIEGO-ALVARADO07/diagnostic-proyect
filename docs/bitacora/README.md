# Bitácora de cambios

> Volver a la [documentación del proyecto](../README.md).

Registro ordenado de los cambios hechos al proyecto tras la revisión técnica de noviembre de 2026.
Cada entrada explica **qué** se cambió, **dónde** y **por qué**, para poder rastrear o revertir decisiones.

## Convenciones

- Una entrada por cambio, numerada en el orden en que se aplicó: `NNN-descripcion-corta.md`.
- Cada entrada indica la fase del plan de mejoras a la que pertenece.
- Las rutas de archivos son relativas a la raíz del repositorio **en la rama `dev`** (donde vive el código); esta rama `docs` solo contiene documentación.
- Cada fase se publicó como un commit en `dev`: fase 1 `4c7dd04`, fase 2 `9ff838b`, fase 3 `85ed289`, fase 4 `b834696`, fase 5 `2ae0476`.

## Plan de mejoras

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Higiene del repositorio, `.env.example`, logging y script de tareas | Completada |
| 2 | Caché del dataset del dashboard por importación | Completada |
| 3 | Enum de estados, limpieza de archivos de compatibilidad, errores uniformes | Completada |
| 4 | División de `DashboardService`, puntajes por clave, `Base` y migraciones en `core` | Completada |
| 5 | Identidad de programas, semestres, regla del global y calidad de datos | Completada |
| 6 | Ajustes de seguridad, CI y frontend | En curso |

## Índice

| # | Fase | Cambio |
|---|---|---|
| 001 | 1 | [Sacar `core/.env` de git y ampliar `.gitignore`](001-env-fuera-de-git.md) |
| 002 | 1 | [Plantilla `.env.example`](002-env-example.md) |
| 003 | 1 | [Configuración de logging](003-logging.md) |
| 004 | 1 | [Script de tareas `tasks.ps1`](004-script-de-tareas.md) |
| 005 | 1 | [Actualización de la documentación de arranque](005-documentacion-arranque.md) |
| 006 | 2 | [Caché en memoria del dataset del dashboard](006-cache-dataset-dashboard.md) |
| 007 | 2 | [Memoizar `normalized_key`](007-memoizar-normalized-key.md) |
| 008 | 2 | [Tests de la caché, benchmark y ajuste de `tasks.ps1 test`](008-tests-y-benchmark-fase-2.md) |
| 009 | 3 | [Enum `ImportStatus` y constantes del dashboard](009-enum-estados-importacion.md) |
| 010 | 3 | [Sesión de BD en `core` y eliminación de archivos de compatibilidad](010-sesion-bd-y-shims.md) |
| 011 | 3 | [Errores uniformes: `ApplicationError` y `HTTPStatus`](011-errores-uniformes.md) |
| 012 | 3 | [Correcciones a `tasks.ps1` (errores de la entrada 004)](012-correcciones-tasks-ps1.md) |
| 013 | 4 | [`Base` del ORM y migraciones fuera del módulo `security`](013-base-y-migraciones-en-core.md) |
| 014 | 4 | [Competencias en un solo lugar y puntajes por clave](014-competencias-y-puntajes-por-clave.md) |
| 015 | 4 | [División de `DashboardService`](015-division-dashboard-service.md) |
| 016 | 4 | [TD PROGRAMAS sin encabezado y verificación de regresión](016-td-programas-sin-encabezado-y-regresion.md) |
| 017 | 5 | [Unificación de programas por nombre normalizado](017-unificacion-de-programas.md) |
| 018 | 5 | [Migración `0004_unify_programs`](018-migracion-0004-programas.md) |
| 019 | 5 | [Semestres normalizados](019-semestres-normalizados.md) |
| 020 | 5 | [Reporte de calidad de datos, regla del global y verificación](020-calidad-de-datos-y-regla-global.md) |
| 021 | 6 | [Interacciones del dashboard frontend](021-dashboard-frontend-interacciones.md) |
| 022 | 6 | [Promedio general del dashboard y contraste con Power BI](022-promedio-general-dashboard.md) |
| 023 | 7 | [Redefinición del proyecto: comparación ESE + CORHUILA](023-redefinicion-ese-corhuila.md) |
| 024 | 7 | [Escala común de niveles y 4 competencias comparables](024-escala-comun-de-niveles.md) |
| 025 | 8 | [Fuente, periodo y momento; un activo por espacio](025-fuente-periodo-y-momento.md) |
| 026 | 9 | [Identidad por correo y programa de CORHUILA desde ESE](026-identidad-por-correo.md) |
| 027 | 9.1 | [Identidad por documento con correos como alias, búsqueda del programa y Momento 4](027-identidad-por-documento-y-momento-4.md) |
| 028 | 10 | [Importación del Excel de CORHUILA y copia de seguridad con un comando](028-importacion-corhuila.md) |
