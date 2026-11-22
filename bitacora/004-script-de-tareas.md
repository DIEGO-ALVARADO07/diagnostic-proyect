# 004 · Script de tareas `tasks.ps1`

- **Fase:** 1 (automatización)
- **Fecha:** 2026-11-21

## Qué se cambió

Archivo nuevo `back/api-reader-excel/tasks.ps1` con estas tareas:

| Tarea | Acción |
|---|---|
| `install` | Crea el `venv` si falta, actualiza `pip` e instala `requirements.txt`. |
| `test` | `python -m unittest discover -s tests` |
| `migrate` | `python -m modules.security.migrations` |
| `bootstrap` | Pide los datos del superadmin (contraseña oculta) o los toma de las variables `BOOTSTRAP_SUPERADMIN_*`. Ejecuta el bootstrap y **siempre** borra esas variables al terminar. |
| `run` | `python -m uvicorn app:app --reload`, con `-Port` y `-BindHost` opcionales. |

Comportamiento común:

- Se ubica en la carpeta del backend y define `PYTHONPATH`, así que funciona desde cualquier carpeta y sin activar el `venv`.
- Antes de `run`, `migrate` y `bootstrap` comprueba que exista `core/.env`. Si encuentra valores cifrados (`gAAAAAB…`) y no está definida `APP_MASTER_KEY`, se detiene con un mensaje claro. **Nunca muestra los valores.**
- Ejecuta Python con `$ErrorActionPreference = "Continue"` y decide por el código de salida. En Windows PowerShell 5.1, cualquier texto que `unittest` o Uvicorn escriban en stderr se convertía en error y abortaba el script.

## Por qué

El arranque documentado exigía entrar a `core/`, definir `PYTHONPATH` a mano y usar `--app-dir .. --reload-dir ..`. Además, la documentación afirmaba que el `.env` "debe estar en `core/` porque Pydantic busca la ruta relativa". Eso no era cierto: `config.py` ya usaba una ruta absoluta. Un solo comando por tarea reduce errores y deja el proceso listo para automatizarlo, por ejemplo en CI.

## Verificación

- `.\tasks.ps1 test`: 33 pruebas, OK, código de salida 0.
- `.\tasks.ps1 run -Port 8765`: Uvicorn arranca y `GET /health` responde `{"status":"ok"}`. Las peticiones quedan registradas en el log.
