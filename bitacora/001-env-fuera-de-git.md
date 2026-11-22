# 001 · Sacar `core/.env` de git y ampliar `.gitignore`

- **Fase:** 1 (higiene del repositorio)
- **Fecha:** 2026-11-21
- **Rama:** `dev`

## Qué se cambió

1. `back/api-reader-excel/core/.env` se dejó de versionar con `git rm --cached`. **El archivo sigue en tu disco**; solo sale del índice de git.
2. `back/api-reader-excel/.gitignore` pasó de 2 reglas a cubrir:
   - variables de entorno: `.env`, `.env.*`, con excepción de `.env.example`;
   - caché de Python (`*.py[cod]`), `.venv/`;
   - herramientas de pruebas y análisis (`.pytest_cache/`, `.coverage`, `htmlcov/`, `.ruff_cache/`, `.mypy_cache/`);
   - archivos de editores y del sistema (`.vscode/`, `.idea/`, `Thumbs.db`, `.DS_Store`).

## Por qué

- El `.env` entró al repositorio en el commit `764a5b6`. Aunque `DB_USER` y `DB_PASSWORD` estén cifrados con Fernet, `DB_HOST`, `DB_PORT` y `DB_NAME` van en texto plano y describen la infraestructura.
- Un `.env` versionado termina sobrescribiéndose entre desarrolladores y entornos (dev, staging, prod).
- La documentación se contradecía: `note.md` decía que era seguro versionarlo y `IMPLEMENTATION.md` decía que no. Se adopta una sola política: **ningún `.env` se versiona**.

## Pendiente o a tener en cuenta

- **El archivo sigue en el historial de git.** Quitarlo del índice no lo borra de los commits anteriores. Si alguna vez se subió con valores sin cifrar, o si el repositorio es o será público, hay que **rotar las credenciales de MySQL** (y la `APP_MASTER_KEY` si se cree comprometida). Reescribir el historial (`git filter-repo`) es opcional y afecta a todos los clones.
- El cambio quedó en el área de preparación (staged), sin commit.
