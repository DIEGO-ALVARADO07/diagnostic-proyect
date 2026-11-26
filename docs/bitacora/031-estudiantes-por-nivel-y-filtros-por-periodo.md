# 031. Estudiantes por nivel, filtros por periodo y "Ver módulo" con filtros

**Fecha:** 26 de noviembre de 2026
**Fase:** 13a
**Rama de código:** `dev` (commit `b3acc77`)

## Cambio de negocio

1. **Los estudiantes salen de los Excel.** La pantalla Estudiantes mostraba las cuentas de usuario con rol estudiante, que se crean una por una. Ahora lista a los estudiantes que llegan en las cargas de ESE y CORHUILA, todos en una sola lista y sin separarlos por prueba. Con los datos reales son 3.243. No hay que crear ninguno a mano. El inicio de sesión de estudiantes queda para después.
2. **Cinco grupos:** Nivel 1, Nivel 2, Nivel 3, Nivel 4 y Sin resultado. **Cada estudiante está en un solo grupo.** Es la base del futuro módulo de cursos: un curso se vinculará a un nivel e inscribirá a todos los estudiantes de ese nivel.
3. **Regla del nivel:**
   - Se toman las filas del estudiante en el periodo y se promedia el puntaje de cada competencia común. Si en ese periodo presentó ESE y CORHUILA, entran las dos.
   - Cada promedio se clasifica con la escala común (1–4).
   - El nivel del estudiante es el promedio de esos niveles, **redondeado hacia abajo**. Ejemplo: 2, 3, 2 y 3 dan 2,5, que queda en Nivel 2. Así no se sube de nivel a nadie.
   - **Sin resultado:** no presentó o no tiene puntajes.
4. **Periodo, como en el dashboard:**
   - Al entrar se ve el **último periodo** con datos.
   - Los filtros son Año → Periodo, y al elegir un año se elige su periodo más reciente.
   - La opción **"Todo el histórico"** muestra a todos, cada uno con el nivel de su periodo más reciente con puntajes.
   - **Elegir un nivel no cambia el periodo.**
5. **Módulo ESE:** los filtros pasan a ser **Año → Periodo → Momento**, como en el dashboard, y se quita el filtro "Simulacro". Un simulacro es justamente un periodo más un momento ("SIMULACRO 2026-1 MOMENTO 2").
   - Arranca en el periodo más reciente y no tiene "Todos los años".
   - "Todo el año" en Periodo muestra el año completo.
6. **"Ver módulo" lleva los filtros del dashboard:**
   - **ESE:** año, periodo, momento y programa. "Sin programa" no se pasa, porque en ESE no existe.
   - **CORHUILA:** el periodo. Ejemplo: si en el dashboard se elige 2026 · Periodo 1 · Momento 2 (149 estudiantes de ESE), el módulo ESE abre con esos filtros y los mismos 149.

## Qué cambió en el código

**Backend**

- `services/student_levels_service.py` (nuevo) tiene `StudentLevelsService.list`. Hace esto:
  1. junta las filas de todas las cargas activas (ESE y cada periodo de CORHUILA);
  2. las agrupa por persona con `DashboardRecord.identity` (estudiante resuelto, documento o correo);
  3. calcula el nivel con `student_level`;
  4. filtra por periodo, nivel, programa y búsqueda;
  5. pagina.
- Endpoint nuevo `GET /excel/dashboard/students` (instructor y superadmin). Recibe:
  - `period` (`AAAA-S` o `all`; sin él, el último);
  - `level` (`1`–`4` o `sin-resultado`);
  - `program_id`, `search`, `page` y `page_size`.
- Respuesta:
  - `groups`, con el conteo por nivel. Ya tiene aplicados el periodo, la búsqueda y el programa, pero no el nivel;
  - `periods`, `period`, `programs`, `filtered_total`, `students` y `rule`.
- `services/dashboard_filters.py`: `moments_by_period` para la cascada del módulo ESE.
- DTO: `StudentLevelItemResponse`, `StudentLevelGroupResponse` y `StudentLevelsResponse`.

**Frontend**

- Pantalla Estudiantes:
  - `partials/students/screen.php` y `style.css`;
  - `js/main.js` (Año → Periodo, 5 tarjetas, búsqueda, programa y paginación de 50 en 50).
- `index.php`: la vista `students` ya no consulta las cuentas de usuario. El menú Usuarios del superadmin sigue igual.
- `shared/data.php`:
  - el recurso `students`;
  - los filtros del módulo ESE ahora también reenvían `period` y `moment`.
- `shared/js/periods.js`: antes estaba en `dashboard/js/`; ahora lo usan el dashboard y Estudiantes.
- `ese/js/*`: periodo y momento en el estado, la URL, los filtros y el historial del estudiante.
- `dashboard/js/main.js`: arma los enlaces "Ver módulo". `shared/compare-side.php` marca esos enlaces con `data-side-module`.

## Verificación

- `python -m unittest discover -s tests`: 130 pruebas OK (antes 123). Las nuevas cubren:
  - el histórico, con un estudiante una sola vez y con un solo nivel;
  - el redondeo hacia abajo;
  - "Sin resultado";
  - los filtros de nivel, programa y búsqueda, y la paginación;
  - el último periodo por defecto y otro periodo con su propio nivel;
  - los momentos por periodo.
- La prueba de endpoints protegidos pasa de 14 a 15.
- En el navegador, con el libro real:
  - **Estudiantes:**
    - 2026-2 tiene 631 estudiantes (185 / 129 / 129 / 138 / 50);
    - 2025-2 más Nivel 1 da 293, sin cambiar el periodo;
    - el histórico tiene 3.243 (1.346 / 873 / 537 / 206 / 281);
    - en el histórico, "Sin programa" suma 31, igual que el módulo CORHUILA.
  - **Módulo ESE:** abre en 2026-2 (184). Al elegir 2025, se elige 2025-2 y el momento vuelve a "Todos".
  - **"Ver módulo"** desde 2026-1 · Momento 2 muestra 149 estudiantes en ESE, igual que el dashboard.
  - No hubo errores en la consola.
