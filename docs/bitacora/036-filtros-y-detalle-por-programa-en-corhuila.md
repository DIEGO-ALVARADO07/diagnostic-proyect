# 036. Filtros, búsqueda y detalle por programa en CORHUILA

**Fecha:** 27 de noviembre de 2026
**Fase:** 15
**Rama de código:** `dev` (commit `543d7fb`)

## Por qué

En el módulo CORHUILA no se podía:
- buscar a un estudiante por nombre, documento o correo;
- filtrar por programa;
- entrar a un programa para ver sus estudiantes y su gráfica, como en el módulo ESE.

Además, desde la fase 14 CORHUILA ya tiene el semestre de cada estudiante (sale de matriculados), pero no había cómo filtrarlo.

## Qué cambió

### Backend

**Endpoint nuevo `GET /excel/dashboard/{import_id}/results`**, para instructor y superadmin. Sirve para cualquier carga (CORHUILA o ESE).

| Parámetro | Qué hace |
|---|---|
| `program_id` | Deja un programa; `sin-programa` también vale. Sin él, todos. Si el programa no está en la carga, `404`. |
| `semester` | Uno de `semester_options` (`SEMESTRE 5`…); `sin-semestre` deja las filas sin semestre. |
| `search` | Hasta 120 caracteres. **Cada palabra** debe estar en el nombre, el documento, el correo o el programa, sin tildes ni mayúsculas. Ejemplo: "ana sistemas" encuentra a Ana en Ingeniería de Sistemas. |
| `page`, `page_size` | Paginación (`page_size` ≤ 50). |

La respuesta (`DashboardResultsResponse`) trae:

- `metrics`: los indicadores y las competencias del programa y el semestre elegidos. **No usa la búsqueda**, que solo cambia la tabla.
- `programs`: el promedio por programa con el semestre aplicado; "Sin programa" va al final.
- `program_options` y `semester_options`: las opciones de los filtros, cada una con cuántas filas tiene si se aplican los demás filtros y la búsqueda.
- `students`: una fila por estudiante y programa (quien tiene doble programa sale dos veces). Cada fila trae:
  - documento y tipo, nombre, correo, programa y semestre;
  - el puntaje de las 4 competencias;
  - `average`: el promedio de esas 4;
  - `level`: el nivel 1–4, con la misma regla que el módulo Estudiantes; `null` si no tiene resultado.

| Archivo | Cambio |
|---|---|
| `modules/excel/services/dashboard_results.py` (nuevo) | `build_results`: filtros, búsqueda por palabras, opciones con conteo, promedio y nivel por fila. |
| `dashboard_query_service.py` y `dashboard_service.py` | `get_results`, que valida que la carga sea visible y la paginación. |
| `routes.py` | La ruta nueva. |
| `dtos/responses/dashboard.py` | `DashboardResultsResponse`, `ResultStudentResponse` y `ResultOptionResponse`. |

### Frontend (vista `corhuila`)

- **Filtros:**
  - **Periodo**;
  - **Programa** y **Semestre**, cada opción con su número de filas, por ejemplo "INGENIERIA DE SISTEMAS (45)";
  - **Buscar estudiante** (nombre, documento, correo o programa), que espera 300 ms mientras se escribe;
  - **Restablecer**.

  Un resumen debajo muestra los filtros activos.
- **Vista general:**
  - los indicadores, la gráfica de competencias y la tabla "Promedio por programa", donde **cada programa se puede pulsar** para abrir su detalle;
  - la tabla **Resultados por estudiante**;
  - la lista "Sin programa".
- **Detalle del programa** (al pulsarlo o al elegirlo en el filtro):
  - "← Todos los programas";
  - el nombre del programa, sus indicadores y su gráfica por competencia;
  - la tabla con solo sus estudiantes.

  La lista "Sin programa" se oculta, salvo en el propio "Sin programa".
- **Tabla de estudiantes:**
  - columnas: nombre y correo, documento con su tipo, programa, semestre y nivel;
  - los puntajes de Lectura, Ciudadanas, Cuantitativo e Inglés, y su promedio;
  - va de 25 en 25.
- **URL:** el estado (`period`, `program_id`, `semester`, `search` y `page`) queda en la URL. Entrar o salir de un programa crea una entrada en el historial, así que **Atrás** del navegador vuelve a la vista anterior.

| Archivo | Cambio |
|---|---|
| `corhuila/screen.php`, `corhuila/js/main.js` y `corhuila/style.css` | Filtros, detalle del programa y tabla de estudiantes. |
| `corhuila/js/results.js` (nuevo) | Dibuja las filas de la tabla. |
| `shared/data.php` | Recurso `results`: valida la carga, el programa, el semestre, la búsqueda (≤ 120) y la página, y pide 25 filas. |
| `shared/compare-side.php` y `shared/js/compare-side.js` | La opción `onOpenProgram` hace que el nombre de cada programa sea un botón. El Dashboard no la usa, así que no cambia. |
| `index.php` | La vista `corhuila` carga también `students/style.css` (insignias de nivel y tabla). |

## Verificación

- **Pruebas:** 167 en total.
  - 7 nuevas en `tests/test_dashboard_results.py`: opciones y conteos, búsqueda por correo, documento y nombre con programa, métricas del programa que no cambian con la búsqueda, filtros de "Sin programa" y semestre, promedio y nivel, paginación y `404`.
  - `test_dashboard` ahora cuenta 17 rutas protegidas.
- `php -l` y `node --check` sin errores en los archivos cambiados.
- **Base real, CORHUILA 2026-2** (solo conteos):

  | Comprobación | Resultado |
  |---|---|
  | Todas las filas | 441 en 18 páginas (incluye las 2 copias del doble programa) |
  | Estudiantes distintos | 398 (hay estudiantes con más de una fila en el archivo) |
  | Programas | 15, ninguno "Sin programa" |
  | Semestres | 4: 1 · 5: 165 · 6: 272 · 7: 1 · sin semestre: 2 |
  | Buscar por documento, correo y nombre | encuentra a la persona en los tres casos |
  | Buscar "sistemas" | 67 filas |
  | Respuesta | unos 10 ms con la caché |

  El promedio de un programa en su detalle coincide con el de la tabla de programas.
- No se probó en el navegador desde la sesión de desarrollo (pide iniciar sesión). Queda para la revisión del usuario.
