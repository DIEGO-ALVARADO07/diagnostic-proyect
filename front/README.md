# Frontend

El frontend es una aplicación PHP que presenta los módulos de la API de diagnóstico. `index.php` conserva el marco de navegación y carga una sola pantalla por solicitud; las pantallas y sus estilos específicos están agrupados bajo `partials/`.

La documentación técnica del backend, sus rutas, configuración, migraciones y pruebas está en [`back/api-reader-excel/IMPLEMENTATION.md`](../back/api-reader-excel/IMPLEMENTATION.md). El índice de documentación del backend está en [`back/README.md`](../back/README.md).

## Estructura

| Ruta | Responsabilidad |
|---|---|
| `index.php` | Verifica sesión, obtiene el perfil, resuelve el menú según el rol, valida la vista solicitada y carga la pantalla permitida. |
| `api_client.php` | Configura la sesión PHP y centraliza las peticiones JSON y `multipart/form-data` a la API. |
| `login.php` | Envía las credenciales a `POST /auth/login` y guarda el token y perfil devueltos en la sesión PHP. |
| `logout.php` | Limpia la sesión PHP y redirige al formulario de acceso. |
| `dashboard.css` | Estilos comunes del marco, navegación, tablas, formularios, avisos y modales. |
| `dashboard.js` | Búsqueda y filtros de tablas, confirmación de desactivación, menú móvil, modal de hojas y estado de carga de Excel. |
| `partials/<modulo>/screen.php` | Plantilla PHP del módulo. |
| `partials/<modulo>/style.css` | Estilos que solo se cargan para el módulo activo. Una vista puede cargar varios (`'style' => [...]` en `index.php`). |
| `partials/<modulo>/js/` | Script del módulo en módulos ES nativos, sin build. `main.js` es el punto de entrada y se carga con `type="module"`. |
| `partials/shared/` | Lo que comparten Dashboard, ESE y CORHUILA: el proxy `data.php`, los estilos de tarjetas y gráficas (`style.css`), la plantilla de una mitad del comparativo (`compare-side.php`) y los módulos JS comunes (`api.js`, `format.js`, `dom.js`, `compare-side.js`, `charts/`). |

Módulos actuales:

- `partials/dashboard/`: inicio. ESE y CORHUILA lado a lado en un periodo; filtros en cascada Año → Periodo → Momento (solo ESE) → Programa, que arrancan en el último periodo cargado; abajo, el programa y la competencia más bajos en común.
- `partials/ese/`: histórico de ESE con filtros (el simulacro solo ofrece los del año elegido), tarjetas de programas y vistas de programa y estudiante.
- `partials/corhuila/`: resultados de CORHUILA por periodo y lista "Sin programa" para asignar el programa a mano o recalcular el cruce.
- `partials/users/`: listado de cuentas para superadmin.
- `partials/create_user/`: creación de instructores y estudiantes.
- `partials/students/`: listado y búsqueda de estudiantes para instructor.
- `partials/report/`: "Importar Excel". Prueba (ESE o CORHUILA) y periodo: solo el actual y el anterior (`periodosDeCarga()` en `index.php`), validado también al recibir el formulario. Acepta `?source=` y `?period=` para llegar con la prueba y el periodo elegidos.
- `partials/profile/`: consulta y edición del perfil propio.

## Vistas y permisos

La vista se selecciona con el parámetro `view`; por ejemplo, `index.php?view=dashboard`. El menú y la lista de vistas permitidas se construyen en `index.php` según el perfil actual:

| Rol | Vistas del menú |
|---|---|
| `superadmin` | Dashboard, ESE, CORHUILA, importar Excel, importaciones, usuarios, crear cuenta y mi perfil |
| `instructor` | Dashboard, ESE, CORHUILA, importar Excel, estudiantes y mi perfil |
| `estudiante` | Mi perfil |

La vista no autorizada vuelve al inicio. Esta restricción es de navegación; el backend sigue siendo quien autoriza cada operación.

## Integración con la API

`api_client.php` centraliza la URL base, el token Bearer, la ejecución cURL y la interpretación de las respuestas. El frontend consume estos endpoints:

| Acción en el frontend | Endpoint |
|---|---|
| Iniciar sesión | `POST /auth/login` |
| Cargar el perfil actual y definir el rol del menú | `GET /users/me` |
| Listar cuentas (superadmin) o consultar estudiantes (instructor) | `GET /users?limit=100` |
| Actualizar el perfil propio | `PATCH /users/me` |
| Crear una cuenta (superadmin) | `POST /users` |
| Desactivar una cuenta (superadmin) | `DELETE /users/{id}` |
| Subir y leer una hoja de Excel | `POST /excel/read` |
| Consultar el histórico de ESE | `GET /excel/dashboard/active`, `GET /excel/dashboard/{import_id}` y consultas de programa/estudiante |
| Dashboard comparativo y módulo CORHUILA | `GET /excel/dashboard/compare?period=&moment=&program_id=` |
| Estudiantes "Sin programa" y asignación manual | `GET /excel/dashboard/review/without-program`, `GET /excel/dashboard/catalog/programs`, `PUT /excel/dashboard/review/students/{id}/program` y `POST /excel/dashboard/corhuila/resolve` |

El frontend solicita `GET /users` únicamente al abrir la vista de usuarios o estudiantes. La búsqueda por texto y el filtro por rol se aplican sobre esos resultados en el navegador.

### Carga de reportes

1. La pantalla de reporte envía el archivo en el campo `file` y el nombre escrito en `sheet_name`, juntos como `multipart/form-data`.
2. Se permiten `.xlsx`, `.xlsm`, `.xls` y `.ods`; la aplicación limita el archivo a 30 MB. La API también valida rol, formato y tamaño.
3. La aplicación muestra el nombre de la hoja leída, el total de filas y una vista previa de hasta 50.
4. Si la API responde `422` con `available_sheets`, se muestra un modal con el nombre ingresado y las hojas disponibles.
5. El resultado y el error de hoja se mantienen temporalmente en la sesión PHP para el redireccionamiento posterior al formulario. No son un historial de reportes.

El dashboard usa los snapshots académicos que persiste la API al importar `BD GEN` y `TD PROGRAMAS`; no es necesario volver a subir el Excel para consultar los resultados. El promedio general mostrado en las tarjetas y los indicadores de programa corresponde al promedio de todas las notas de competencia no nulas. El valor `average_global` sigue disponible en la API con su significado original, basado en la columna GLOBAL del libro. Las tarjetas conservan hasta dos decimales y el detalle individual mantiene el puntaje GLOBAL propio del estudiante.

## Sesión y seguridad

- La sesión PHP dura ocho horas; la cookie se configura con `HttpOnly` y `SameSite=Lax`.
- El token de API se conserva del lado del servidor en la sesión PHP y se envía en el encabezado `Authorization: Bearer`.
- Si una petición protegida recibe `401`, el cliente elimina la sesión y redirige al login.
- Los formularios de escritura incluyen un token CSRF de sesión.
- La interfaz oculta opciones por rol, pero no sustituye las comprobaciones de permisos de FastAPI.
- `logout.php` limpia la sesión local del frontend. En el estado actual no envía `POST /auth/logout` para revocar el token en la API.

## Requisitos y ejecución local

Se requiere PHP 7.4 o posterior con la extensión **cURL** habilitada. La API debe estar activa antes de usar las pantallas protegidas. Su configuración y arranque se explican en la [guía del backend](../back/api-reader-excel/IMPLEMENTATION.md).

La URL base de la API está definida como `API_BASE_URL` en `api_client.php` y por defecto es `http://127.0.0.1:8000`. Si la API escucha en otro host o puerto, actualiza esa constante.

Desde PowerShell, en la raíz del proyecto:

```powershell
Set-Location C:\Users\USUARIO\Desktop\diagnostic-proyect
php -S 127.0.0.1:8081
```

Abre `http://127.0.0.1:8081/front/login.php`. Se sirve la raíz del proyecto para que las redirecciones a `/front/login.php` funcionen. En Apache/Laragon, configura de forma equivalente la raíz del proyecto como document root.

### Límite de carga de PHP

Para aceptar archivos cercanos al límite de la API, configura `php.ini` con valores como estos y reinicia el servidor web:

```ini
upload_max_filesize = 30M
post_max_size = 32M
```

`post_max_size` debe ser mayor que `upload_max_filesize` para incluir el límite multipart. Si PHP rechaza el archivo antes de que llegue a la aplicación, revisa estos valores.

## Validación

Para comprobar la sintaxis de las pantallas PHP con el ejecutable de PHP disponible en el entorno:

```powershell
Get-ChildItem .\front -Recurse -Filter *.php | ForEach-Object { php -l $_.FullName }
```

La carga de páginas y la lectura de reportes requieren que la API esté ejecutándose y que exista una sesión autenticada.
