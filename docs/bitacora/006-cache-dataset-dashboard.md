# 006 · Caché en memoria del dataset del dashboard

- **Fase:** 2 (rendimiento)
- **Fecha:** 2026-11-21

## Problema

Cada petición a `GET /excel/dashboard/{id}`, `/programs/{id}` y `/students/{doc}` llamaba a `DashboardService._load_dataset`. Ese método:

1. lee **todas** las filas de `academic_results` de la importación;
2. lee `academic_programs` y `td_programas_reference`;
3. convierte cada fila ORM en un `DashboardRecord` y arma los índices por programa y por estudiante.

Después de importar, `_import_response` repetía todo el proceso. Con 20.000 filas, cada clic en un filtro costaba alrededor de 1 segundo, incluso en SQLite en memoria. Con MySQL por red, más.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/modules/excel/services/dashboard_cache.py` | **Nuevo.** `DashboardDatasetCache`: una LRU acotada (3 entradas por defecto) y segura entre hilos, con `Lock`, porque las rutas corren en un threadpool. Métodos: `get`, `put`, `invalidate`, `clear`. Con `max_entries=0` la caché queda desactivada. |
| `back/api-reader-excel/modules/excel/services/dashboard_service.py` | `DashboardService` recibe `dataset_cache` (inyectable para tests). Nuevo método `_dataset_for()`: busca en la caché y, si no está, carga de la base, registra en el log el tiempo y las filas, y guarda el resultado. `_get_dataset` y `_import_response` usan `_dataset_for`. `delete_import` invalida la entrada. `_load_dataset` ahora devuelve colecciones inmutables. |
| `back/api-reader-excel/modules/excel/entities/dashboard.py` | `DashboardDataset` usa `tuple` y `Mapping` en lugar de `list` y `dict`, y tiene un docstring que explica por qué. |

## Decisiones

- **Por qué se puede cachear:** una importación `ACTIVE` o `HISTORICAL` es una instantánea. Sus filas solo se escriben durante `persist_snapshot` y nunca se modifican después. Solo se cachean esos dos estados, sin `deleted_at`.
- **La caché no decide la visibilidad.** `_get_dataset` sigue leyendo primero la fila de `excel_imports` (por clave primaria, que es barato) y valida el estado, `deleted_at` y el rol. Por eso, si Uvicorn corre con varios procesos y cada uno tiene su propia caché, una importación desactivada deja de servirse en todos aunque su caché siga llena. La invalidación en `delete_import` solo libera memoria.
- **Datos inmutables:** el mismo `DashboardDataset` se comparte entre peticiones e hilos. Con tuplas y `MappingProxyType`, un cambio accidental en el código lanza `TypeError` en vez de corromper los datos de otras peticiones.
- **La importación precarga la caché:** `_import_response` usa `_dataset_for`, así que la primera consulta después de importar ya es rápida.
- **Límite de 3 entradas:** la activa más un par de históricas que consulte el superadmin. Cada dataset de 20.000 filas ocupa decenas de MB. El límite es un parámetro del constructor.
- **Dos peticiones simultáneas sin caché** pueden cargar el mismo dataset a la vez. Es aceptable: el resultado es idéntico y solo cuesta una lectura de más.

## A tener en cuenta en fases futuras

- **Fase 5:** si se permite renombrar o unificar programas (`canonical_name` o alias), los datasets en caché quedarían con el nombre anterior. Esa fase debe llamar a `dataset_cache.clear()` después de cualquier cambio en `academic_programs`.
- La caché vive en el proceso: se vacía al reiniciar Uvicorn y la primera consulta vuelve a cargar desde la base de datos.
