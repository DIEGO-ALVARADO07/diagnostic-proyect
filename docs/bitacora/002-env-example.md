# 002 · Plantilla `core/.env.example`

- **Fase:** 1 (higiene del repositorio)
- **Fecha:** 2026-11-21

## Qué se cambió

Archivo nuevo `back/api-reader-excel/core/.env.example` con:

- las variables obligatorias (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`) con valores de ejemplo;
- la variable opcional nueva `LOG_LEVEL` (ver entrada 003);
- comentarios sobre el cifrado con Fernet y sobre dónde va `APP_MASTER_KEY`: en la terminal, nunca en el archivo.

## Por qué

Al dejar de versionar el `.env` (entrada 001), quien clone el repositorio necesita saber qué variables definir. La plantilla documenta la configuración sin exponer valores reales.

## Uso

```powershell
Copy-Item core\.env.example core\.env
```
