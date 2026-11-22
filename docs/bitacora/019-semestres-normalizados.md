# 019 · Semestres normalizados

- **Fase:** 5 (decisión del 2026-11-22)
- **Fecha:** 2026-11-22

## Problema

La columna SEMESTRE de `CORHUILA.xlsm` mezcla `SEMESTRE 4` (556 filas) con `4` (288), y lo mismo pasa con 7 (`SEMESTRE 7` con 697 filas y `7` con 210). El filtro mostraba **9 opciones en vez de 7**, y filtrar por `SEMESTRE 4` dejaba fuera las filas escritas como `4`.

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `modules/excel/services/dashboard_normalizer.py` | Nuevo `canonical_semester()`: un número entero positivo (`"4"`, `4.0`, `" 10 "`) pasa a `SEMESTRE N`. Cualquier otro texto se devuelve limpio y sin cambios. |
| `modules/excel/services/dashboard_processor.py` | `semester_key` se calcula sobre el semestre canónico. `semester_raw` sigue guardando el texto original. |
| `modules/excel/services/dashboard_dataset_loader.py` | El semestre que ven el dashboard y los filtros es `canonical_semester(semester_raw)`. Se calcula al cargar, así que también **corrige las importaciones anteriores** sin migrar datos. |

## Notas

- `0` no se convierte: no es un semestre válido y se deja tal cual para que se note.
- En importaciones anteriores, la columna `semester_key` conserva el valor viejo. Ninguna lectura la usa, porque los filtros trabajan sobre el semestre canónico calculado al cargar.

## Efecto con el Excel real

Semestres en el filtro: `4, 7, SEMESTRE 1, …` (9) → `SEMESTRE 1, SEMESTRE 10, SEMESTRE 4, SEMESTRE 6, SEMESTRE 7, SEMESTRE 8, SEMESTRE 9` (7). Cambia `semester_key` en 498 filas (288 + 210).
