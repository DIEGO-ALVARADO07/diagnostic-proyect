# Estado de entrega y continuidad entre sesiones

> Actualizado el 23 de noviembre de 2026. Permite retomar el desarrollo en otra sesión o equipo sin depender del historial de chat. No contiene credenciales ni valores de `.env`.

## Ramas del repositorio

| Rama | Contenido |
|---|---|
| `dev` | Código: backend en `back/api-reader-excel/` y frontend en `front/`. HEAD: `2e0d3b2`; los cambios de promedios descritos abajo siguen sin commit. |
| `docs` | Esta documentación (`docs/`) y la [bitácora de cambios](bitacora/README.md). |
| `main` | Rama principal; aún no recibe los cambios de las fases 1–5. |

Para trabajar en ambas a la vez, usa un *worktree* para `docs` (`git worktree add ../diagnostic-proyect-docs docs`) y así no cambias de rama en la carpeta del código. No copies credenciales, tokens ni el contenido de `core/.env` a Git ni a esta carpeta.

## Plan de mejoras (revisión técnica de noviembre de 2026)

Cada cambio está explicado en orden (qué, dónde y por qué) en la [bitácora](bitacora/README.md).

| Fase | Contenido | Estado | Commit en `dev` |
|---|---|---|---|
| 1 | `.env` fuera de Git, `.env.example`, logging y `tasks.ps1` | Completada | `4c7dd04` |
| 2 | Caché en memoria del dataset del dashboard (~1 s → 5–150 ms por consulta) | Completada | `9ff838b` |
| 3 | Enum de estados, sesión de BD única en `core`, sin módulos de compatibilidad, errores uniformes | Completada | `85ed289` |
| 4 | `DashboardService` dividido, competencias por clave, `Base` y migraciones en `core`, `TD PROGRAMAS` sin encabezado | Completada | `b834696` |
| 5 | Programas unificados (migración `0004`), semestres normalizados, reporte de calidad de datos | Completada | `2ae0476` |
| 6 | Seguridad (limpieza de tokens vencidos, cerrar sesiones al cambiar contraseña, límite de intentos de login), `requirements-dev.txt` con ruff/pytest, CI en GitHub Actions, frontend (URL de API configurable, CSRF en login) | **Pendiente** | — |
| 7–13 | Comparación ESE + CORHUILA: escala común, fuente/periodo, identidad por correo, importación CORHUILA, API comparativa, frontend dividido, cursos genéricos | **Pendiente** — ver [plan](11-plan-de-refactorizacion.md) | — |

Decisiones de negocio tomadas en la fase 5 (22/11/2026):

- Unificar programas que solo difieren en tildes, mayúsculas o espacios.
- Tratar `4` como `SEMESTRE 4`.
- Mantener la regla del GLOBAL del Excel (competencias vacías = 0).
- Los códigos `N` y `P` de "Comunicación escrita" tienen significado desconocido: siguen como sin puntaje y se reportan en `source_audit.data_quality` para que alguien los aclare.

## Tareas operativas pendientes

1. **Aplicar las migraciones en cada MySQL** (con copia de seguridad: `0004` fusiona programas y no se revierte):

   ```powershell
   $env:APP_MASTER_KEY = "<clave>"
   .\tasks.ps1 migrate
   ```

2. **Credenciales:** `core/.env` estuvo versionado hasta el commit `764a5b6` y sigue en el historial de Git. `DB_USER` y `DB_PASSWORD` van cifrados, pero `DB_HOST`, `DB_PORT` y `DB_NAME` están en texto plano. Si el repositorio es o será público, conviene rotar las credenciales de MySQL.
3. Aclarar con la institución qué significan los códigos `N` y `P`.

## Qué está construido

### Backend

- API FastAPI (monolito modular): `modules/security` (autenticación con token opaco, usuarios, roles) y `modules/excel` (lectura de Excel y dashboard académico).
- `POST /excel/read` lee una hoja sin persistir; `POST /excel/dashboard/import` guarda snapshots de `BD GEN` y la referencia visible de `TD PROGRAMAS` en MySQL (no guarda el archivo).
- Dashboard: vista global, programa y estudiante con filtros; auditoría frente a `TD PROGRAMAS` y reporte de calidad de datos; caché en memoria por importación.
- Operación con `tasks.ps1` (install, migrate, bootstrap, run, test) y logging configurable.
- 58 pruebas automatizadas en SQLite.

### Frontend

- PHP con sesión del lado del servidor y llamadas autenticadas a la API; no requiere Node.js.
- Pantallas por rol: dashboard, usuarios, estudiantes, reporte, perfil e importaciones (superadmin).
- El dashboard usa el proxy `front/partials/dashboard/data.php` y dibuja gráficos SVG.
- Ajuste de usabilidad del dashboard: tarjetas de seis programas por página, selector limitado por filtros activos y búsqueda de estudiantes sin recargar la vista.

Guías: [Instalación y uso](03-instalacion-y-operacion.md), [API](04-api.md), [Flujo del dashboard](09-flujo-dashboard-academico.md), [Frontend](08-frontend.md).

## Validación registrada (22/11/2026)

- `.\tasks.ps1 test`: 58 pruebas OK.
- `pyflakes` sobre `modules`, `core`, `app`, `api`, `tests`, `migrations` y `scripts`: sin avisos.
- Libro real `CORHUILA.xlsm` (3.819 filas): las fases 3 y 4 no cambiaron ningún resultado (comparación completa de respuestas y filas guardadas). La fase 5 solo cambió lo decidido: 27 → 17 programas y 9 → 7 semestres; KPIs, historiales y auditoría (14 diferencias) iguales.
- Uvicorn real: `/health` responde y las rutas protegidas sin token devuelven `401` con `WWW-Authenticate: Bearer`.

Las pruebas de migraciones se ejecutan sobre SQLite; no demuestran que ya se aplicaron en el MySQL de cada equipo.

## Mejora del dashboard frontend (23/11/2026)

- Se reemplazó el gráfico comparativo lateral por una cuadrícula amplia de tarjetas; cada tarjeta abre el detalle del programa.
- Se distribuyen seis programas por página: 17 programas generan 3 páginas y 12 programas del año 2024 generan 2. Los botones tienen límites y no repiten páginas.
- El selector de programa usa la lista ya filtrada por año y simulacro, no el catálogo global.
- La búsqueda del programa refresca solo la tabla de estudiantes mediante fetch y mantiene el foco sin desplazar intencionalmente la página al inicio.
- Se corrigió la ruta de carga del nivel estudiante para solicitar su historial, en vez de llamarse recursivamente.
- El proxy de overview pide hasta 50 programas en una sola respuesta, suficiente para el catálogo actual. Si en el futuro se exceden 50 programas, habrá que ampliar la paginación de overview manteniendo opciones de filtro completas.

## Comparación de promedio general con Power BI (23/11/2026)

- Se agregó `average_general`, promedio conjunto de las notas no nulas de las cinco competencias de intentos presentados. `average_global` (columna J) y `simple_competence_average` conservan sus significados.
- La desviación `general_standard_deviation` es muestral; las desviaciones anteriores permanecen poblacionales.
- El overview ordena por promedio general; el historial estudiantil entrega `program_average_general`. Las tarjetas y los KPI del frontend usan **Promedio general**, conservan hasta dos decimales y mantienen compatibilidad con una API anterior sin el nuevo campo.
- La verificación autenticada contra el snapshot local de `CORHUILA.xlsm`, con `SIMULACRO 2026-2 MOMENTO 1`, reprodujo a dos decimales los 14 promedios reportados por Power BI. Sistemas `149,43`, Negocios Internacionales `142,03`, Industrial `140,61`, Financiera y Bursátil `140,44` y Administración Comercial `138,85`; el promedio GLOBAL existente se mantuvo en `144`, `136,57`, `123,8`, `137,82` y `126`, respectivamente.
- `.\venv\Scripts\python.exe -m unittest discover -s tests`: 61 pruebas OK, incluidas las nuevas comprobaciones de promedio, desviación muestral, nulos y orden. `.\tasks.ps1 test` no pudo iniciarse porque la política de ejecución de PowerShell bloquea scripts en el entorno; se ejecutó el mismo `unittest` desde el venv.

La bitácora técnica está en [mejora de interacción del dashboard](bitacora/021-dashboard-frontend-interacciones.md). Para ejecutar validaciones, sigue [Pruebas y desarrollo](07-pruebas-y-desarrollo.md).

## Archivos de referencia en el código (rama `dev`)

| Archivo | Responsabilidad |
|---|---|
| `back/api-reader-excel/tasks.ps1` | Tareas de instalación, migración, arranque y pruebas. |
| `back/api-reader-excel/core/` | Configuración, sesión por petición, `Base` ORM, errores y logging. |
| `back/api-reader-excel/migrations/` | Alembic: `runner.py` y revisiones `0001`–`0004`. |
| `back/api-reader-excel/modules/excel/routes.py` | Endpoints del dashboard y controles de acceso. |
| `back/api-reader-excel/modules/excel/services/` | Importación, consultas, caché, auditoría, reglas de programas y calidad de datos. |
| `back/api-reader-excel/modules/excel/entities/` | Modelos ORM y dominio (`ImportStatus`, `Competency`, dataset). |
| `back/api-reader-excel/scripts/bench_dashboard.py` | Medición de rendimiento. |
| `front/index.php`, `front/partials/` | Navegación por rol y pantallas. |

## Al retomar

1. `git fetch` y revisa `git status` en `dev` y en el worktree de `docs`.
2. Lee la [bitácora](bitacora/README.md) para entender los cambios recientes.
3. Sigue [Instalación y uso](03-instalacion-y-operacion.md) y aplica las migraciones pendientes.
4. Continúa con la fase 6 o con los objetivos del proyecto (clasificación pedagógica y recomendación de cursos, aún no implementados).
