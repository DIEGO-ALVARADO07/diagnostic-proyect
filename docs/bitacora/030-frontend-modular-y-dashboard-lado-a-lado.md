# 030. Frontend en módulos, dashboard lado a lado y módulos ESE y CORHUILA

**Fecha:** 26 de noviembre de 2026
**Fase:** 12 (12a y 12b)
**Rama de código:** `dev` (commits `b52c39d` y `f098f42`)

## 12a: `dashboard.js` dividido en módulos ES

El archivo `front/partials/dashboard/dashboard.js` tenía 1.116 líneas, así que se dividió en módulos ES nativos que se cargan con `type="module"` y no necesitan compilación. **No cambia nada visible ni de comportamiento.**

- Punto de entrada: `js/main.js`.
- `js/context.js` reúne raíz, estado, elementos y acciones compartidas. Así las vistas y el controlador no se importan entre sí en círculo.
- El resto se reparte por responsabilidad:
  - `api.js`, `state.js`, `filters.js`, `metrics.js`, `format.js`, `dom.js`, `controller.js` y `events.js`;
  - `charts/` (`bars`, `bubbles`, `svg` y `trend`);
  - `views/` (`overview`, `program` y `student`).

## 12b: cambio de negocio

1. **Dashboard principal con ESE y CORHUILA lado a lado,** cada uno en una mitad y en el mismo periodo. Cada mitad tiene:
   - 4 KPI: promedio, nivel promedio, estudiantes y presentaciones;
   - las barras de las 4 competencias comunes;
   - la tabla de programas, con "Sin programa" al final.

   Debajo van el programa y la competencia más bajos en común. Si a una prueba le falta el archivo del periodo, su mitad dice **"A la espera del archivo"**. El botón para subirlo solo aparece cuando ese periodo todavía se puede cargar.
2. **Al entrar se ve el último periodo cargado.** Los filtros van en cascada: **Año → Periodo → Momento (solo ESE) → Programa**, y solo ofrecen combinaciones que tienen datos.
   - Al elegir un año, se elige su periodo más reciente.
   - Al cambiar de año o de periodo, el momento vuelve a "Todos". Así no se cruzan, por ejemplo, 2026 y un momento de 2024.
3. **Módulo ESE:** es el histórico, el antiguo dashboard. En esta fase el simulacro solo ofrecía los del año elegido; en la [031](031-estudiantes-por-nivel-y-filtros-por-periodo.md) se cambió por Periodo y Momento.
4. **Módulo CORHUILA:**
   - los resultados de un periodo con archivo de CORHUILA;
   - la lista **"Sin programa"**, con un select de programa y Guardar por estudiante (la asignación manual manda sobre ESE);
   - el botón **"Recalcular cruce"**.
5. **Solo se pueden subir el periodo actual y el anterior,** y la lista se actualiza sola con la fecha:

   | Fecha | Periodos que se pueden subir |
   |---|---|
   | Noviembre de 2026 | 2026-2 y 2026-1 |
   | Enero de 2027 | 2027-1 y 2026-2 (para subir tarde el semestre que acaba de cerrar) |
   | Julio de 2027 | 2027-2 y 2027-1 |

   El servidor también lo valida al recibir el formulario. Si se pudiera subir un periodo viejo con datos de otro año, se perdería la lógica del periodo.
6. **Menú:** Dashboard, ESE, CORHUILA e Importar Excel (antes "Leer reporte"), y después las opciones de cada rol.

## Qué cambió en el código

**Backend**

- `services/dashboard_compare_service.py`:
  - `compare(..., period=None)`: sin periodo usa el último cargado;
  - devuelve `filters.periods` (los periodos con filas de ESE o con un archivo de CORHUILA), `filters.corhuila_periods` y `selected_filters.period`.
- `services/dashboard_filters.py`: `simulations_by_year`.
- `routes.py`: `GET /excel/dashboard/compare` acepta `period` (`AAAA-1` o `AAAA-2`).

**Frontend**

- Las carpetas quedaron así:

  | Carpeta | Contenido |
  |---|---|
  | `front/partials/shared/` | Proxy `data.php`, estilos, gráficas, `api.js` (con `apiPost` y CSRF), `dom.js`, `format.js` y la plantilla de cada mitad (`compare-side.php` y `compare-side.js`). |
  | `front/partials/dashboard/` | Pantalla comparativa nueva. |
  | `front/partials/ese/` | Histórico de ESE (lo que antes era `dashboard/`). |
  | `front/partials/corhuila/` | Módulo CORHUILA y tabla "Sin programa". |

- `shared/data.php` agrega estos recursos:
  - `compare`, `catalog` y `without_program`;
  - `assign_program` y `resolve`, que son POST y piden el token CSRF.
- `index.php`:
  - `periodosDeCarga()` calcula los periodos de carga y se valida al subir;
  - vistas `dashboard`, `ese` y `corhuila`, y el menú nuevo.
- `report/screen.php`: solo ofrece los periodos de carga, marcados "(actual)" y "(anterior)". Se puede preseleccionar desde `?source=` y `?period=`.

## Verificación

- `python -m unittest discover -s tests`: 123 pruebas OK. Las nuevas cubren elegir otro periodo y los simulacros agrupados por año.
- `compileall` y `php -l` sin errores; todos los imports de los módulos JS resuelven.
- En el navegador, con el libro real:
  - el dashboard abre en 2026-2, con ESE 137,67 (184 estudiantes) y CORHUILA 192,52 (398);
  - la cascada 2025 → 2025-2 → 2025-1 → Momento 1 funciona;
  - CORHUILA queda "a la espera", sin botón de carga, en los periodos viejos;
  - el módulo CORHUILA muestra 31 estudiantes "Sin programa".
- Guardar el programa y Recalcular cruce no se probaron con los datos reales, porque los modifican.
