# 005 · Actualización de la documentación de arranque

- **Fase:** 1
- **Fecha:** 2026-11-21

## Qué se cambió

| Archivo | Cambio |
|---|---|
| `back/api-reader-excel/IMPLEMENTATION.md` | Se reescribió la sección "Configuración y ejecución en Windows". Ahora tiene una tabla de comandos de `tasks.ps1`, la creación de `core/.env` desde la plantilla, la instalación, el bootstrap, el arranque y las migraciones. Se corrigió la afirmación errónea sobre la ruta relativa del `.env`. La sección de pruebas ahora usa `.\tasks.ps1 test` y aclara que las pruebas no necesitan MySQL. |
| `back/note.md` | Aviso al inicio: la guía es de una estructura anterior, los `.env` ya no se versionan, y siguen vigentes el esquema de roles y el cifrado con Fernet. |

## Por qué

Las entradas 001 a 004 cambiaron cómo se configura y se arranca el backend. Sin actualizar la documentación, alguien que siga los pasos anteriores obtendría resultados distintos o versionaría de nuevo un `.env`.
