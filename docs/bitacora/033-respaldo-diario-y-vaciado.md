# 033. Copia diaria solo con cambios y vaciado de la base para empezar desde cero

**Fecha:** 26 de noviembre de 2026
**Fase:** operación
**Rama de código:** `dev`

## Por qué

- Para mostrarle al ingeniero el recorrido completo, desde subir el primer Excel, hace falta una forma segura de **vaciar la base** sin borrar las cuentas ni la estructura.
- Hace falta una **copia diaria automática** que solo se guarde **cuando cambió algo**, para no llenar el disco con copias idénticas.

## Qué cambió

| Archivo | Cambio |
|---|---|
| `scripts/backup_db.py` | `--if-changed` y `--keep N`; huella de los datos, estado en `.ultimo-respaldo.json` y limpieza de copias viejas. |
| `scripts/reset_db.py` (nuevo) | Vacía los datos académicos con copia previa y confirmación. |
| `tasks.ps1` | Comandos `backup-daily`, `schedule-backup`, `unschedule-backup` y `reset`. |

**`scripts/backup_db.py`**

- `--if-changed`: antes de copiar calcula una huella de los datos (`CHECKSUM TABLE` de cada tabla, sin `api_access_tokens`, porque iniciar sesión no es un cambio de datos). La compara con la de la última copia, guardada en `.ultimo-respaldo.json` en la carpeta de respaldos. Si es igual y ese archivo sigue existiendo, no crea otra copia.
- Toda copia (manual o diaria) actualiza la huella.
- `--keep N`: deja solo las N copias más recientes con la misma etiqueta; las de otras etiquetas no se tocan.

**`scripts/reset_db.py`**

1. Exige `--confirm <nombre de la base>`.
2. Hace la copia `antes-vaciar`; si falla, no borra nada.
3. Borra, en orden seguro para las llaves foráneas, todos los datos académicos: inscripciones, cursos, resultados, TD PROGRAMAS, importaciones (activas e históricas), correos, estudiantes, alias y programas. En MySQL reinicia los `AUTO_INCREMENT`.
4. Conserva `excel_dashboard_state`, `alembic_version` y, salvo `--include-users`, `api_users` y `api_access_tokens`.

**`tasks.ps1`**

| Comando | Qué hace |
|---|---|
| `backup-daily` | Copia `diario` solo si hubo cambios (`-Keep` opcional). |
| `schedule-backup -At HH:mm` | Tarea de Windows "Diagnostico academico - respaldo diario". Corre con el usuario actual (con `APP_MASTER_KEY`). Si el equipo estaba apagado, corre al encenderlo. Si falla, reintenta cada hora hasta 6 veces. Registra cada ejecución en `%USERPROFILE%\respaldos\respaldo-diario.log`, en UTF-8. |
| `unschedule-backup` | Quita la tarea. |
| `reset` | Explica qué se borra, pide escribir el nombre de la base y llama a `scripts.reset_db` (`-IncludeUsers` opcional). |

## Verificación

- `python -m unittest discover -s tests`: 146 pruebas OK (antes 139). Las nuevas cubren:
  - la huella: el orden de las tablas no importa, las sesiones no cuentan y un cambio en un curso sí cuenta;
  - el estado y la limpieza con `--keep`;
  - que toda tabla esté clasificada (se vacía o se conserva a propósito);
  - el vaciado conservando cuentas, o borrándolas con `--include-users`;
  - el rechazo de una confirmación equivocada.
- Con la base real:
  - `backup-daily` creó `excel_reader_2026-11-26_1534_diario.sql` (11,1 MiB) y la segunda vez respondió "Sin cambios… no se creó otra copia";
  - `reset` con un nombre equivocado no borró nada (3.243 estudiantes intactos).
- La tarea quedó programada a las 02:30 en el equipo de desarrollo. Al ejecutarla a mano dio resultado 0 y escribió "Sin cambios" en el log.
- La base real **no se vació**: lo hace el usuario cuando vaya a la demostración.
