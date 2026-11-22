# 012 · Correcciones a `tasks.ps1` (errores de la entrada 004)

- **Fase:** 3 (corrige la fase 1)
- **Fecha:** 2026-11-22

## Cómo se detectó

Al probar la fase 3 contra Uvicorn real, `GET /users/me` sin token devolvió **500** en vez de 401. La causa no era el código de la fase 3:

- `core/.env` tiene `DB_USER` y `DB_PASSWORD` cifrados con Fernet, y la terminal de prueba no tenía `APP_MASTER_KEY`;
- la primera petición que pide una sesión crea `Settings`, y el descifrado falla.

Esto ya pasaba antes. Pero `tasks.ps1 run` **debía haberlo detectado y detenerse con un aviso**, y no lo hizo. Revisando aparecieron dos errores.

## Errores y correcciones

1. **No detectaba credenciales cifradas entre comillas.** El patrón `=\s*gAAAAAB` no admite comillas, y el `.env` real usa `DB_USER = "gAAAAAB…"`. Ahora el patrón es `=\s*["']?gAAAAAB`. Con esto, `run`, `migrate` y `bootstrap` se detienen con el mensaje *"core\.env tiene credenciales cifradas. Define APP_MASTER_KEY…"*.
2. **Tildes corruptas en los mensajes** ("terminÇü con cÇüdigo"). Windows PowerShell 5.1 lee como ANSI los `.ps1` guardados en UTF-8 **sin BOM**. El archivo se guarda ahora en UTF-8 **con BOM** (`EF BB BF`).

## Verificación

- Sin `APP_MASTER_KEY`, `.\tasks.ps1 run` y `.\tasks.ps1 migrate` se detienen de inmediato con el aviso y las tildes correctas.
- Con credenciales ficticias en variables de entorno (tienen prioridad sobre `core/.env`), Uvicorn responde 401 con `WWW-Authenticate: Bearer` en las rutas protegidas.

## Para ti

Para arrancar la API necesitas definir la clave en la terminal antes de `.\tasks.ps1 run`:

```powershell
$env:APP_MASTER_KEY = "<clave>"
```

## Herramienta local

Para revisar imports sin usar instalé `pyflakes` en tu `venv`. **No** se añadió a `requirements.txt`: las dependencias de desarrollo (pyflakes o ruff, pytest) se organizan en la fase 6.
