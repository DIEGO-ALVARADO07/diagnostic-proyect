# 007 · Memoizar `normalized_key`

- **Fase:** 2 (rendimiento)
- **Fecha:** 2026-11-21

## Problema

Después de la caché (entrada 006), un perfilado con `cProfile` de `get_overview` mostró que **~70 % del tiempo restante** se iba en `normalized_key()`: unas 80.000 llamadas por petición con 20.000 filas. La función hace `casefold`, descomposición Unicode NFKD y quita tildes, y se llama:

- por cada registro y cada atributo en `_filter_options` (simulacro, grupo, semestre y tipo);
- por cada registro en `_matches` cuando hay filtros.

Los valores distintos son muy pocos (decenas de simulacros, grupos, etc.), así que se recalculaba lo mismo miles de veces.

## Qué se cambió

`back/api-reader-excel/modules/excel/services/dashboard_normalizer.py`: `normalized_key` lleva `@functools.lru_cache(maxsize=8192)` y un docstring que lo explica.

## Por qué es seguro

- Es una función pura: la misma entrada siempre da la misma salida, sin efectos secundarios.
- Todas las llamadas pasan `str` o `None`, que se pueden usar como clave de caché. Lo comprobé buscando todos los usos.
- `lru_cache` es seguro entre hilos.
- Con `maxsize=8192` la memoria queda acotada. Las búsquedas por nombre de estudiante, que tienen muchos valores distintos, solo rotan entradas.
