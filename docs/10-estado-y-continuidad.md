# Estado de entrega y continuidad entre sesiones

> Resumen de trabajo actualizado el 20 de noviembre de 2026. Este documento permite retomar el desarrollo en otra sesión o equipo sin depender del historial de chat. No contiene credenciales ni valores de `.env`.

## Repositorios y transferencia

Hay dos carpetas de trabajo independientes:

- `diagnostic-proyect/`: código del backend en `back/api-reader-excel/` y frontend en `front/`.
- `diagnostic-proyect-docs-worktree/`: esta documentación, en `docs/`.

La documentación debe transferirse junto con el código al que se refiere. Los comandos y rutas de los documentos técnicos son relativos a la raíz del proyecto, salvo que se indique lo contrario. Antes de continuar en otro equipo, revisa `git status --short` en ambos worktrees y conserva cualquier modificación sin commit. No copies credenciales, tokens ni contenido del archivo `core/.env` a Git o a esta carpeta.

Al preparar este resumen, el código del proyecto tenía cambios pendientes (incluidos cambios staged) y la documentación tenía cambios sin commit. No se creó ningún commit ni se subieron cambios; cada worktree debe sincronizarse por separado si se requiere llevarlos a otro dispositivo.

## Qué está construido

### Frontend

- Frontend PHP con inicio y cierre de sesión, sesión del lado del servidor y llamadas autenticadas a la API. No requiere Node.js ni npm para ejecutarse.
- Navegación y pantallas separadas según el rol. `front/index.php` mantiene el marco principal y carga el módulo solicitado desde `front/partials/`.
- Estilo institucional verde, sidebar y pantallas modulares para dashboard, usuarios, estudiantes, reporte, perfil e importaciones.
- El instructor puede consultar estudiantes, importar el libro y consultar el dashboard académico.
- El superadmin dispone, además, de administración de usuarios e historial administrativo de importaciones.
- El dashboard consulta datos persistidos mediante el proxy PHP `front/partials/dashboard/data.php`; `dashboard.js` dibuja los gráficos SVG y gestiona las vistas global, programa y estudiante.

La guía funcional y de instalación está en [Frontend PHP](08-frontend.md).

### Backend y datos académicos

- FastAPI mantiene separados el endpoint de lectura temporal `POST /excel/read` y el flujo persistente `POST /excel/dashboard/import`.
- La importación académica usa las hojas `BD GEN` y `TD PROGRAMAS`, procesa los resultados y guarda snapshots relacionales en MySQL. No guarda el archivo binario.
- Cada importación tiene hash y estado. Se conserva cada fila de origen; las consultas usan el mismo `import_id` para evitar mezclar snapshots.
- El frontend carga global, programas y estudiantes desde endpoints autenticados; sus filtros y gráficos no consultan directamente MySQL.

La especificación de contratos está en [API y contratos](04-api.md); el flujo de datos completo, en [Flujo del dashboard académico](09-flujo-dashboard-academico.md).

## Permisos y desactivación lógica

| Acción | Superadmin | Instructor |
|---|---:|---:|
| Importar snapshot | Sí | Sí |
| Consultar snapshot activo | Sí | Sí |
| Consultar snapshots históricos disponibles | Sí | No |
| Abrir el módulo de historial administrativo | Sí | No |
| Ver registros desactivados como `DELETED` | Sí | No |
| Desactivar un snapshot | Sí | No |

El historial tiene un módulo independiente **Importaciones** en el frontend. La desactivación no es un borrado físico:

- La API marca `excel_imports.deleted_at`; conserva el registro y sus resultados.
- El estado original guardado no se reemplaza; el endpoint administrativo presenta `DELETED` cuando `deleted_at` tiene valor.
- Las consultas normales ocultan los snapshots desactivados y las consultas directas por ID responden `404`.
- Se pueden desactivar snapshots `ACTIVE`, `HISTORICAL` o `FAILED`; no `PROCESSING` ni `VALIDATED`.
- Si se desactiva el snapshot activo, `excel_dashboard_state.active_import_id` se limpia. El dashboard queda sin resultados hasta una nueva importación.
- Reimportar exactamente el contenido desactivado responde `409`; no existe restauración automática.

Rutas relevantes:

| Método | Ruta | Acceso y resultado |
|---|---|---|
| `GET` | `/excel/dashboard/active` | Instructor o superadmin; consulta el snapshot activo. |
| `GET` | `/excel/dashboard/imports` | Superadmin; lista importaciones no desactivadas. |
| `GET` | `/excel/dashboard/admin/imports?limit=100` | Superadmin; lista todos los estados, incluidos `DELETED`. Lo usa el módulo **Importaciones**. |
| `DELETE` | `/excel/dashboard/imports/{import_id}` | Superadmin; desactivación lógica de `ACTIVE`, `HISTORICAL` o `FAILED`. |
| `GET` | `/excel/dashboard/{import_id}` y consultas hijas | Instructor solo para el activo; superadmin para activos e históricos no desactivados. |

## Migraciones: requisito antes de probar

La revisión `0003_soft_delete_excel_imports` agrega la columna nullable `deleted_at` a `excel_imports`. Sin aplicarla, las nuevas consultas pueden fallar aunque el frontend y el código de la API estén actualizados. El servidor no migra la base automáticamente.

Desde PowerShell, en la raíz de `back/api-reader-excel/`, usa el entorno virtual del proyecto y el wrapper que valida esquemas legacy:

```powershell
.\venv\Scripts\python.exe -m modules.security.migrations
```

Si la terminal está en `back/api-reader-excel/core/`, la ruta del intérprete equivalente es:

```powershell
..\venv\Scripts\python.exe -m modules.security.migrations
```

No uses `python -m alembic upgrade head` para saltarte el wrapper de migraciones. Configura localmente `core/.env` y `APP_MASTER_KEY` cuando aplique. La revisión `0003` fue verificada con SQLite en las pruebas; la aplicación a una base MySQL real debe confirmarse en el entorno destino antes de usar la interfaz.

## Validación registrada

En el workspace al preparar esta nota pasaron:

- `python -m unittest discover -s tests -p test_dashboard.py -v`: 10 pruebas.
- `python -m unittest discover -s tests -p test_security_migrations.py -v`: 3 pruebas.
- `php -l` para `front/index.php`, el módulo `imports` y la pantalla de perfil.
- `git diff --check` en el repositorio de código y en el worktree de documentación.

Las pruebas de migraciones se ejecutan sobre SQLite temporal; no demuestran que la migración ya se haya aplicado a la base MySQL configurada en cada equipo.

## Archivos de referencia en el código

| Archivo | Responsabilidad |
|---|---|
| `front/index.php` | Navegación, control de vistas por rol y flujo de acciones de importación. |
| `front/partials/imports/screen.php` y `style.css` | Historial administrativo y acción de desactivación. |
| `front/partials/dashboard/dashboard.js` y `data.php` | Consultas del dashboard, visualizaciones SVG y proxy autenticado PHP. |
| `back/api-reader-excel/modules/excel/routes.py` | Endpoints y controles de acceso del dashboard. |
| `back/api-reader-excel/modules/excel/services/dashboard_service.py` | Importación, autorización de snapshots y desactivación lógica. |
| `back/api-reader-excel/modules/excel/entities/academic.py` | Entidad de importación con `deleted_at`. |
| `back/api-reader-excel/modules/security/migrations/versions/0003_soft_delete_excel_imports.py` | Migración de la marca de desactivación lógica. |
| `back/api-reader-excel/tests/test_dashboard.py` | Pruebas de dashboard, permisos, retención y desactivación. |
| `back/api-reader-excel/tests/test_security_migrations.py` | Cadena y reversión de migraciones. |

## Precaución al retomar

En el workspace de desarrollo existe una modificación local del usuario en `back/api-reader-excel/core/config.py`, que resuelve `core/.env` junto al archivo de configuración. No reemplazar ni revertir ese archivo sin revisar primero su diff. Tampoco sobrescribir cambios pendientes del frontend o backend al sincronizar entre equipos.

Para continuar, revisa primero [Instalación y operación](03-instalacion-y-operacion.md), [Pruebas y desarrollo](07-pruebas-y-desarrollo.md) y el estado de ambos worktrees. No se implementó recomendación automática de cursos ni clasificación pedagógica; son objetivos futuros del proyecto.
