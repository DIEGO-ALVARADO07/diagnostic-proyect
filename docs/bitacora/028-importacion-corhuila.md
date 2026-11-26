# 028. Importación del Excel de CORHUILA y copia de seguridad con un comando

**Fecha:** 26 de noviembre de 2026
**Fase:** 10
**Ramas de código:** `dev` (backend y frontend)

## Qué cambió

1. **Mismo endpoint para las dos pruebas.** `POST /excel/dashboard/import` exige ahora `source` (`ESE` o `CORHUILA`) y `period` (`AAAA-1` o `AAAA-2`). Cada periodo se carga con sus dos archivos.
   - **ESE** sigue con un solo activo, porque trae toda la historia, pero la carga queda marcada con su periodo. `data_quality.period_moment.upload_period_rows` dice cuántas filas son de ese periodo; `0` indica que quizá se eligió mal.
   - **CORHUILA** se activa en su espacio `CORHUILA:<periodo>`, sin tocar ESE ni otros periodos.
2. **Lector de CORHUILA** (`repositories/corhuila_workbook_repository.py`):
   - Lee la hoja `Calificaciones`; si no existe, usa la primera hoja con los encabezados esperados.
   - **Obligatorios:** `Nombre`, `Apellido(s)`, `Dirección de correo` y los cuatro `Cuestionario:… (Real)`.
   - **Opcional:** `Número de ID`. Se usa para el cruce por documento en cuanto venga lleno.
3. **Reglas de cada fila** (`services/corhuila_processor.py`), iguales a ESE:
   - `-` o vacío = sin puntaje; `0` cuenta.
   - Presentó si tiene al menos un puntaje.
   - Comunicación escrita no se evalúa.
   - El año sale del periodo.
4. **Estudiante y programa guardados al leer** (`persist_corhuila_snapshot`):
   - Primero se busca al estudiante en el ESE activo (documento → correo → nombre completo único). Si aparece, se usa ese estudiante y su correo de CORHUILA queda como alias.
   - Si no aparece, se crea (o se reutiliza por documento o correo) y queda **por revisar**.
   - El programa de ESE Momento 2 y el método de coincidencia quedan **guardados en la fila de CORHUILA**: el dashboard no repite el cruce al consultar.
   - Si después un ESE trae a ese estudiante, el pendiente se **une** al de ESE y la fila de CORHUILA se actualiza sola.
5. **Lista "por revisar":** `GET /excel/dashboard/review/without-program?period=` devuelve los estudiantes de CORHUILA activos sin programa (ambiguos, sin coincidencia o sin Momento 2), para revisarlos con la base institucional.
6. **Auditoría de CORHUILA** (`data_quality.corhuila`):
   - hoja leída, filas, presentaron, no presentaron, presentaron parcialmente;
   - filas sin correo, filas con documento, correos repetidos;
   - coincidencias por método y cuántas quedaron sin programa.
7. **Consultas:** las de resumen, programa y estudiante funcionan con el `import_id` de CORHUILA. Las filas sin programa se agrupan en **"Sin programa"**.
8. **Frontend** (Importar reporte): selectores **Prueba** (ESE/CORHUILA) y **Periodo de la carga**. Por defecto viene el periodo actual.
9. **`.\tasks.ps1 backup`** (`scripts/backup_db.py`):
   - Hace la copia con `mysqldump` usando las credenciales de `core/.env`. Las pasa en un archivo temporal que se borra al terminar, nunca en la línea de comandos.
   - Busca `mysqldump` en el PATH o en Laragon.
   - Guarda en `%USERPROFILE%\respaldos\<base>`, fuera del repositorio.
   - Incluye `DROP/CREATE DATABASE`, así que restaurar deja la base igual que en la copia.
   - Opciones: `-Label antes-0008`, `-BackupDir`, `-MysqlDump`.
   - `migrate` recuerda hacerla antes.

## Decisiones (26/11/2026)

- El periodo se elige siempre al subir, para ESE y para CORHUILA (por ahora).
- Los estudiantes de CORHUILA que no están en ESE se crean y quedan en la lista "por revisar", para solicitar acceso de lectura a la base institucional.
- El programa de CORHUILA se guarda al leer el archivo, no se calcula en cada consulta.

## Caso encontrado por las pruebas

Si CORHUILA se importa **antes** que ESE, un estudiante sin documento quedaba creado aparte y el ESE posterior no lo unía con el de su documento: su correo seguía en el pendiente. Ahora, al importar ESE, un estudiante **sin documento** con el mismo correo se une al del documento (resultados y correos incluidos).

## Cómo aplicarla

No tiene migración. Reemplaza los archivos y ejecuta:

```powershell
.\tasks.ps1 test
```

El frontend ya envía la prueba y el periodo. Quien use la API directamente (Swagger, PowerShell) debe enviar `source` y `period`.

## Verificación

- `python -m unittest discover -s tests`: 108 pruebas OK (antes 95). Las nuevas cubren:
  - importación de CORHUILA con las cinco formas de coincidencia;
  - reglas de puntaje;
  - reutilización y creación de estudiantes;
  - lista por revisar;
  - resolución al llegar ESE después;
  - espacios activos;
  - filas del periodo de ESE;
  - no duplicar;
  - errores de hoja y periodo;
  - hoja con otro nombre;
  - funciones del respaldo.
- `pyflakes` sin avisos; `php -l` sin errores en `index.php` y `report/screen.php`.
- Respaldo probado con un `mysqldump` simulado: crea el archivo y borra el de credenciales.
- Libro real de CORHUILA: _(completar: `data_quality.corhuila` y total de la lista por revisar)_.
