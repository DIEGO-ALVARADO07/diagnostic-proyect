# Bitácora de cambios

Registro ordenado de los cambios hechos al proyecto tras la revisión técnica de noviembre de 2026.
Cada entrada explica **qué** se cambió, **dónde** y **por qué**, para poder rastrear o revertir decisiones.

## Convenciones

- Una entrada por cambio, numerada en el orden en que se aplicó: `NNN-descripcion-corta.md`.
- Cada entrada indica la fase del plan de mejoras a la que pertenece.
- Las rutas son relativas a la raíz del repositorio.

## Plan de mejoras

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Higiene del repositorio, `.env.example`, logging y script de tareas | Completada |
| 2 | Caché del dataset del dashboard por importación | Pendiente |
| 3 | Enum de estados, limpieza de archivos de compatibilidad, errores uniformes | Pendiente |
| 4 | División de `DashboardService`, puntajes por clave, `Base` y migraciones en `core` | Pendiente |
| 5 | Identidad de programas y regla del global calculado (requiere decisión de negocio) | Pendiente |
| 6 | Ajustes de seguridad, CI y frontend | Pendiente |

## Índice

| # | Fase | Cambio |
|---|---|---|
| 001 | 1 | [Sacar `core/.env` de git y ampliar `.gitignore`](001-env-fuera-de-git.md) |
| 002 | 1 | [Plantilla `.env.example`](002-env-example.md) |
| 003 | 1 | [Configuración de logging](003-logging.md) |
| 004 | 1 | [Script de tareas `tasks.ps1`](004-script-de-tareas.md) |
| 005 | 1 | [Actualización de la documentación de arranque](005-documentacion-arranque.md) |
