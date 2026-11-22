# 015 · División de `DashboardService`

- **Fase:** 4 (estructura)
- **Fecha:** 2026-11-22

## Problema

`modules/excel/services/dashboard_service.py` tenía **980 líneas** y mezclaba seis responsabilidades:

- importar y activar libros;
- listar y desactivar importaciones;
- consultas (overview, programa, estudiante);
- armar el dataset desde el ORM y la caché;
- filtros y conversión a DTOs;
- la auditoría contra TD PROGRAMAS.

Era difícil de leer, probar y cambiar sin tocar algo ajeno.

## Qué se cambió

| Archivo | Líneas | Responsabilidad |
|---|---:|---|
| `dashboard_service.py` | 131 | **Punto de entrada**: compone los servicios, comparte la caché y conserva la interfaz que usan las rutas y las pruebas. Solo delega. |
| `dashboard_import_service.py` | 237 | Importar (con deduplicación por hash), `_activate` (ACTIVE/HISTORICAL), listar y desactivar. |
| `dashboard_query_service.py` | 383 | Overview, programa, estudiante, importación activa y validación de visibilidad por rol y estado. |
| `dashboard_dataset_loader.py` | 186 | ORM → `DashboardDataset` inmutable, con caché. |
| `dashboard_filters.py` | 102 | `matches`, `filter_records`, opciones de filtros, búsqueda de estudiantes. |
| `dashboard_mappers.py` | 79 | Registros y filas ORM → DTOs de respuesta. |
| `dashboard_audit.py` | 83 | `build_source_audit` (TD PROGRAMAS frente a BD GEN), con constantes con nombre para la tolerancia y el máximo de diferencias. |

`tests/test_dashboard_cache.py` ahora espía `DashboardDatasetLoader.read_from_database`, el antiguo `DashboardService._load_dataset`.

## Decisiones

- **Se mantiene `DashboardService` como fachada.** Las rutas y 6 pruebas lo usan, y garantiza que importación y consultas compartan **la misma** caché. Sin la fachada, cada ruta tendría que armar esa composición a mano.
- **Separación lectura/escritura.** `DashboardImportService` depende de `DashboardQueryService` solo para devolver el resumen tras importar. Las consultas no dependen de la importación.
- **Funciones puras donde no hay estado.** Filtros, mappers y auditoría son funciones de módulo, no métodos estáticos de una clase. Se prueban y reutilizan sin instanciar nada.
- **La lógica se copió sin cambios.** Solo hay dos simplificaciones equivalentes: `next(r.simulation for r in matched)` pasa a `matched[0].simulation` (la lista nunca está vacía en ese punto), y el mensaje de tamaño de página usa `MAX_PAGE_SIZE` en vez de un "50" fijo (el texto resultante es el mismo).

## Verificación

- 45 pruebas OK y `pyflakes` sin avisos.
- La foto de regresión del Excel real es idéntica (entrada 016).
