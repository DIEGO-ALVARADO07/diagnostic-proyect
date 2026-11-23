# Frontend PHP

## Propósito y alcance actual

El frontend ofrece la interfaz web para iniciar sesión y consumir la API Diagnostic. Está implementado en PHP y renderiza las pantallas en el servidor; no requiere Node.js, npm ni un framework JavaScript para ejecutarse.

La pantalla de inicio muestra el saludo y el dashboard académico con gráficos de los resultados persistidos. Las demás opciones del menú abren una pantalla por separado. El frontend puede administrar cuentas, consultar estudiantes, importar libros Excel como snapshots y actualizar el perfil según el rol autenticado.

## Estructura del frontend

La aplicación vive en `front/` en la raíz del proyecto.

| Ruta | Responsabilidad |
|---|---|
| `front/index.php` | Verifica sesión, consulta el perfil, prepara el menú según el rol, valida la vista solicitada y carga solo su pantalla. Procesa los formularios y las acciones de cuenta. |
| `front/api_client.php` | Inicia la sesión PHP, configura su duración, adjunta el token Bearer y centraliza las solicitudes JSON y multipart con cURL. |
| `front/login.php` | Envía las credenciales a la API y conserva el token y el perfil en la sesión PHP. |
| `front/logout.php` | Cierra la sesión local del frontend y redirige al formulario de acceso. |
| `front/dashboard.css` | Define colores, tipografía, navegación, componentes compartidos y adaptación responsive. |
| `front/dashboard.js` | Maneja búsqueda y filtros de tablas, confirmación de acciones destructivas y menú móvil. |
| `front/partials/dashboard/dashboard.js` | Consulta el dashboard persistido, gestiona filtros y navegación entre programas y estudiantes, y dibuja gráficos SVG. |
| `front/partials/dashboard/data.php` | Proxy autenticado de mismo origen para las consultas del dashboard; protege la consulta de estudiantes con CSRF y una referencia de sesión. |
| `front/partials/<modulo>/screen.php` | Plantilla PHP del módulo. |
| `front/partials/<modulo>/style.css` | Estilos específicos del módulo; `index.php` carga únicamente los de la vista activa. |

Módulos de pantalla:

| Módulo | Función |
|---|---|
| `dashboard/` | Resumen global de TD PROGRAMAS, comparación por programa y vistas de detalle de programa y estudiante. |
| `users/` | Directorio de cuentas activas, búsqueda, filtro por rol y desactivación para superadmin. |
| `create_user/` | Formulario para crear cuentas de instructor o estudiante. |
| `students/` | Consulta y búsqueda de estudiantes para instructor. |
| `report/` | Importación de snapshots Excel con las hojas `BD GEN` y `TD PROGRAMAS`. |
| `profile/` | Consulta y actualización del perfil propio. |
| `imports/` | Historial de todos los snapshots, solo para superadmin; permite desactivar importaciones activas, antiguas o fallidas. |

El marco común —barra lateral, encabezado y pie— se mantiene en `index.php`; las plantillas parciales contienen el contenido de cada pantalla.

## Navegación y permisos de interfaz

La vista se selecciona con el parámetro `view`, por ejemplo `front/index.php?view=dashboard`. El usuario no ve todas las secciones a la vez: cada solicitud incluye una única pantalla dentro del marco común. Si un rol intenta abrir una vista no incluida en su menú, el frontend vuelve al inicio y presenta un aviso.

| Rol | Vistas disponibles |
|---|---|
| `superadmin` | Inicio, usuarios, crear cuenta, leer reporte, importaciones y mi perfil. |
| `instructor` | Inicio, estudiantes, leer reporte y mi perfil. |
| `estudiante` | Mi perfil. |

La API es la autoridad para los permisos. Ocultar una opción o restringir una vista en PHP mejora la navegación, pero no sustituye la autorización del backend.

## Flujo de datos con la API

1. `login.php` envía `username` y `password` a `POST /auth/login`.
2. Si el login es correcto, PHP regenera el identificador de sesión y conserva `access_token` y `user` del lado del servidor.
3. En las visitas a `index.php`, el frontend consulta `GET /users/me` para actualizar el perfil y construir el menú con el rol actual.
4. El frontend solicita `GET /users?limit=100` solamente al abrir las vistas de usuarios o estudiantes. El buscador y el filtro por rol trabajan sobre ese listado en el navegador.
5. `api_client.php` adjunta `Authorization: Bearer <token>` a las rutas protegidas. Si recibe `401`, limpia la sesión local y redirige al login.
6. El dashboard académico usa el proxy PHP `partials/dashboard/data.php`, que consulta el snapshot activo o las vistas de programa y estudiante con la sesión Bearer.

| Acción | Rol en la interfaz | Endpoint |
|---|---|---|
| Inicio de sesión | Todos | `POST /auth/login` |
| Consultar perfil y rol | Todos | `GET /users/me` |
| Listar cuentas activas | Superadmin | `GET /users?limit=100` |
| Consultar estudiantes | Instructor | `GET /users?limit=100` |
| Crear instructor o estudiante | Superadmin | `POST /users` |
| Desactivar una cuenta | Superadmin | `DELETE /users/{id}` |
| Actualizar perfil propio | Todos | `PATCH /users/me` |
| Importar snapshot de Excel | Instructor y superadmin | `POST /excel/dashboard/import` |
| Consultar todos los estados de importación | Superadmin (módulo Importaciones) | `GET /excel/dashboard/admin/imports?limit=100` |
| Desactivar snapshot activo, histórico o fallido | Superadmin | `DELETE /excel/dashboard/imports/{import_id}` |
| Consultar dashboard académico | Instructor y superadmin | `GET /excel/dashboard/active`; instructor queda limitado al snapshot activo. Superadmin puede consultar también snapshots históricos. |

## Módulos y flujos

### Inicio

`partials/dashboard/` muestra el saludo y consulta el snapshot activo. La vista global presenta los indicadores y tarjetas grandes para los programas; cada tarjeta abre el detalle del programa, con su desempeño por asignatura y la tabla de estudiantes. Las tarjetas se muestran en páginas de seis, así que los 17 programas actuales se reparten en tres páginas y al filtrar por 2024 los 12 programas disponibles ocupan dos.

La comparación lateral de gráficos se retiró para dar espacio a los programas y sus nombres. El filtro de programa se construye con los programas que devuelve la consulta ya filtrada por año y simulacro, por eso no ofrece programas ajenos al contexto seleccionado. Las tarjetas, el KPI institucional y los promedios del detalle muestran el `average_general` calculado sobre todas las notas de competencia no nulas de los intentos presentados. El backend ordena por esa misma métrica para que el orden visible de las tarjetas refleje el resultado general.

La etiqueta es **Promedio general** y los valores conservan hasta dos decimales. Los puntajes `global_score` de cada estudiante no cambian: siguen mostrando el valor individual de la columna GLOBAL. Si una versión anterior de la API no envía `average_general`, el frontend conserva compatibilidad mostrando `average_global`.

La búsqueda de estudiantes por nombre o documento se aplica con una solicitud asíncrona: actualiza la tabla y su paginación sin ocultar ni volver a cargar el resto del detalle. El campo conserva el foco y la interfaz no desplaza la página al inicio; el navegador puede ajustar el desplazamiento si la tabla más corta reduce la altura total del contenido. La paginación de programas también se resuelve en la vista, con límites explícitos y botones desactivados al llegar al inicio o al final.

Los filtros de año, asignatura y simulacro se conservan al navegar. Las gráficas del detalle se construyen con SVG nativo y usan los valores agregados por la API.

El detalle individual solicita una referencia aleatoria protegida por sesión en vez de incluir el documento del estudiante en la URL. La información del dashboard pasa por `partials/dashboard/data.php`; el navegador no envía peticiones a la base de datos ni recibe el token Bearer.

### Usuarios y estudiantes

- La vista de usuarios presenta hasta 100 cuentas activas recibidas de `GET /users`. El superadmin puede buscar por nombre, correo o usuario, filtrar por rol y desactivar cuentas.
- La vista de estudiantes usa el mismo endpoint con el rol instructor; el servicio de backend ya excluye superadmins. El frontend filtra las cuentas con rol `estudiante` y permite buscarlas por texto.
- El formulario de creación envía nombre, usuario, correo, rol y contraseña inicial. La API requiere una contraseña de al menos 12 caracteres y restringe los roles creados a instructor o estudiante.
- La desactivación se confirma en el navegador antes de enviar el `DELETE`; las reglas de protección de cuentas y del último superadmin las aplica el backend.

### Reporte de Excel

1. La pantalla `partials/report/` permite seleccionar el libro y advierte que debe contener las hojas `BD GEN` y `TD PROGRAMAS`.
2. PHP envía `file` como `multipart/form-data` a `POST /excel/dashboard/import`; no solicita el nombre de una hoja.
3. Se aceptan `.xlsx`, `.xlsm`, `.xls` y `.ods`; el frontend y la API limitan el archivo a 30 MB.
4. La API persiste un snapshot y lo activa solo cuando valida el libro. El dashboard consulta después los datos guardados; no es necesario volver a subir el mismo contenido para leerlo.
5. Si se sube una importación histórica idéntica, la API la devuelve sin reactivarla. La interfaz informa esa diferencia al usuario.

### Perfil

El formulario consulta los datos actuales del usuario y los actualiza con `PATCH /users/me`. El cambio de contraseña es opcional; si se envía, la API exige un mínimo de 12 caracteres.

### Importaciones

El menú del superadmin abre `partials/imports/`, un módulo independiente que consulta el endpoint administrativo y muestra todos los estados, incluidas las importaciones desactivadas. El botón **Desactivar** se ofrece para snapshots `ACTIVE`, `HISTORICAL` o `FAILED` y requiere confirmación. La acción es lógica: conserva el registro y sus datos, pero excluye el snapshot de los endpoints normales; el superadmin lo sigue viendo como `DELETED`. Si se desactiva la importación activa, el dashboard queda sin datos hasta que se importe otro libro. El backend rechaza intentos de desactivar estados en proceso o validados.

## Sesiones y seguridad

- La sesión PHP se configura para ocho horas y la cookie usa `HttpOnly` y `SameSite=Lax`.
- El token Bearer se guarda en la sesión del servidor PHP, no en `localStorage` del navegador.
- Los formularios de escritura incluyen un token CSRF de sesión.
- El cliente redirige al login cuando una ruta protegida devuelve `401`.
- `logout.php` destruye la sesión PHP y elimina su cookie. En el estado actual no llama a `POST /auth/logout`, así que no revoca de inmediato el token almacenado por la API; el token conserva su vencimiento backend.
- La validación de roles y permisos en FastAPI sigue siendo obligatoria para todas las acciones.

## Requisitos y ejecución local

Se requiere PHP 7.4 o posterior y la extensión cURL. La API debe estar activa en `http://127.0.0.1:8000`, que es el valor de `API_BASE_URL` en `front/api_client.php`. Para usar otro host o puerto, se actualiza esa constante.

Sigue primero la [guía de instalación y operación del backend](03-instalacion-y-operacion.md). Luego, desde la raíz del proyecto —la carpeta que contiene `front/`— inicia el servidor PHP:

```powershell
php -S 127.0.0.1:8081
```

Abre `http://127.0.0.1:8081/front/login.php`. Servir la raíz del proyecto permite que la redirección de sesión a `/front/login.php` apunte al archivo correcto. En Apache/Laragon configura esa misma raíz como document root, o ajusta la ruta de redirección si se publica `front/` como raíz del sitio.

Para aceptar archivos cercanos al límite configurado por la API, ajusta `php.ini` y reinicia el servidor web:

```ini
upload_max_filesize = 30M
post_max_size = 32M
```

`post_max_size` debe ser mayor que `upload_max_filesize` para incluir el encabezado y los campos multipart. Si PHP rechaza un archivo antes de ejecutar el formulario, revisa estos límites.

## Comprobación local

Desde la raíz del proyecto, se puede validar la sintaxis de las plantillas y scripts PHP con:

```powershell
Get-ChildItem .\front -Recurse -Filter *.php | ForEach-Object { php -l $_.FullName }
```

Para verificar la integración funcional se requiere la API levantada, una cuenta activa y una sesión iniciada desde `front/login.php`. No se necesita Node.js para ejecutar la interfaz: el navegador se encarga de ejecutar `dashboard.js`.
