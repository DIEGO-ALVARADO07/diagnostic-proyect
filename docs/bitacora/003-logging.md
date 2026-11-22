# 003 · Configuración de logging

- **Fase:** 1
- **Fecha:** 2026-11-21

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/core/paths.py` | **Nuevo.** Constantes `CORE_DIR` y `ENV_FILE` (ruta absoluta de `core/.env`). |
| `back/api-reader-excel/core/config.py` | Importa `ENV_FILE` desde `core.paths` en lugar de calcularlo. Elimina el `import Path` que ya no se usaba. Sin cambios de comportamiento. |
| `back/api-reader-excel/core/logging_config.py` | **Nuevo.** `configure_logging()` configura el logger raíz con formato `fecha nivel logger: mensaje`. `resolve_log_level()` busca el nivel en este orden: variable de entorno `LOG_LEVEL`, luego `core/.env`, luego `INFO`. Un valor inválido vuelve a `INFO`. |
| `back/api-reader-excel/app/__init__.py` | `create_app()` llama a `configure_logging()` al inicio. |

## Por qué

- `modules/excel/routes.py` (`TimedExcelRoute`) y `modules/excel/repositories/workbook_repository.py` ya escribían logs `INFO` con tiempos de subida, lectura y respuesta. Nadie configuraba el logging, así que Python solo mostraba `WARNING` o superior y esos datos se perdían.
- El nivel se lee **sin instanciar `Settings`** para que la app pueda crearse sin credenciales de base de datos. Las pruebas dependen de esto.
- `ENV_FILE` se movió a `core/paths.py` porque importar `core.config` crea `Settings` de inmediato y exige las variables de MySQL. Así, logging y configuración comparten la misma ruta sin duplicarla.

## Efecto visible

- Al ejecutar la API aparecen líneas como `2026-11-21 23:15:47 INFO     modules.excel.routes: Excel HTTP request completed: ...`.
- Los avisos de `fastexcel` ("Could not determine dtype…") ahora salen con el mismo formato. Antes salían sin formato. Se atenderán en una fase posterior.
- Los logs de Uvicorn no se duplican, porque Uvicorn usa sus propios handlers.
