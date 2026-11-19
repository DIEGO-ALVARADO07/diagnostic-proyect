# Frontend PHP

## Propósito y alcance actual

El frontend ofrece la interfaz web para iniciar sesión y consumir la API Diagnostic. Está implementado en PHP y renderiza las pantallas en el servidor; no requiere Node.js, npm ni un framework JavaScript para ejecutarse.

La pantalla de inicio muestra el saludo del usuario y un espacio reservado para futuros gráficos. Las demás opciones del menú abren una pantalla por separado. Actualmente el frontend puede administrar cuentas, consultar estudiantes, leer un archivo Excel y actualizar el perfil según el rol autenticado.

Los resultados de Excel no se guardan en la base de datos. Por eso el espacio de gráficos todavía no presenta métricas reales; la persistencia y el análisis pedagógico pertenecen a una fase futura.

## Estructura del frontend

La aplicación vive en `front/` en la raíz del proyecto.

| Ruta | Responsabilidad |
|---|---|
| `front/index.php` | Verifica sesión, consulta el perfil, prepara el menú según el rol, valida la vista solicitada y carga solo su pantalla. Procesa los formularios y las acciones de cuenta. |
| `front/api_client.php` | Inicia la sesión PHP, configura su duración, adjunta el token Bearer y centraliza las solicitudes JSON y multipart con cURL. |
| `front/login.php` | Envía las credenciales a la API y conserva el token y el perfil en la sesión PHP. |
| `front/logout.php` | Cierra la sesión local del frontend y redirige al formulario de acceso. |
| `front/dashboard.css` | Define colores, tipografía, navegación, componentes compartidos y adaptación responsive. |
| `front/dashboard.js` | Maneja búsqueda y filtros de tablas, confirmación de desactivación, menú móvil, modal de hojas y estado de carga de Excel. |
| `front/partials/<modulo>/screen.php` | Plantilla PHP del módulo. |
| `front/partials/<modulo>/style.css` | Estilos específicos del módulo; `index.php` carga únicamente los de la vista activa. |

Módulos de pantalla:

| Módulo | Función |
|---|---|
| `dashboard/` | Saludo y espacio vacío de preparación para gráficos futuros. |
| `users/` | Directorio de cuentas activas, búsqueda, filtro por rol y desactivación para superadmin. |
| `create_user/` | Formulario para crear cuentas de instructor o estudiante. |
| `students/` | Consulta y búsqueda de estudiantes para instructor. |
| `report/` | Selección de Excel y hoja, presentación del resultado y modal para errores de nombre de hoja. |
| `profile/` | Consulta y actualización del perfil propio. |

El marco común —barra lateral, encabezado y pie— se mantiene en `index.php`; las plantillas parciales contienen el contenido de cada pantalla.

## Navegación y permisos de interfaz

La vista se selecciona con el parámetro `view`, por ejemplo `front/index.php?view=dashboard`. El usuario no ve todas las secciones a la vez: cada solicitud incluye una única pantalla dentro del marco común. Si un rol intenta abrir una vista no incluida en su menú, el frontend vuelve al inicio y presenta un aviso.

| Rol | Vistas disponibles |
|---|---|
| `superadmin` | Inicio, usuarios, crear cuenta, leer reporte y mi perfil. |
| `instructor` | Inicio, estudiantes, leer reporte y mi perfil. |
| `estudiante` | Inicio y mi perfil. |

La API es la autoridad para los permisos. Ocultar una opción o restringir una vista en PHP mejora la navegación, pero no sustituye la autorización del backend.

## Flujo de datos con la API

1. `login.php` envía `username` y `password` a `POST /auth/login`.
2. Si el login es correcto, PHP regenera el identificador de sesión y conserva `access_token` y `user` del lado del servidor.
3. En las visitas a `index.php`, el frontend consulta `GET /users/me` para actualizar el perfil y construir el menú con el rol actual.
4. El frontend solicita `GET /users?limit=100` solamente al abrir las vistas de usuarios o estudiantes. El buscador y el filtro por rol trabajan sobre ese listado en el navegador.
5. `api_client.php` adjunta `Authorization: Bearer <token>` a las rutas protegidas. Si recibe `401`, limpia la sesión local y redirige al login.

| Acción | Rol en la interfaz | Endpoint |
|---|---|---|
| Inicio de sesión | Todos | `POST /auth/login` |
| Consultar perfil y rol | Todos | `GET /users/me` |
| Listar cuentas activas | Superadmin | `GET /users?limit=100` |
| Consultar estudiantes | Instructor | `GET /users?limit=100` |
| Crear instructor o estudiante | Superadmin | `POST /users` |
| Desactivar una cuenta | Superadmin | `DELETE /users/{id}` |
| Actualizar perfil propio | Todos | `PATCH /users/me` |
| Leer hoja de un Excel | Instructor y superadmin | `POST /excel/read` |

## Módulos y flujos

### Inicio

`partials/dashboard/` muestra el saludo y una zona amplia para los gráficos que se incorporarán en otra etapa. La pantalla no solicita el listado de usuarios ni datos de reportes. La API actual no persiste los resultados que harían falta para poblar esos gráficos.

### Usuarios y estudiantes

- La vista de usuarios presenta hasta 100 cuentas activas recibidas de `GET /users`. El superadmin puede buscar por nombre, correo o usuario, filtrar por rol y desactivar cuentas.
- La vista de estudiantes usa el mismo endpoint con el rol instructor; el servicio de backend ya excluye superadmins. El frontend filtra las cuentas con rol `estudiante` y permite buscarlas por texto.
- El formulario de creación envía nombre, usuario, correo, rol y contraseña inicial. La API requiere una contraseña de al menos 12 caracteres y restringe los roles creados a instructor o estudiante.
- La desactivación se confirma en el navegador antes de enviar el `DELETE`; las reglas de protección de cuentas y del último superadmin las aplica el backend.

### Reporte de Excel

1. La pantalla `partials/report/` presenta el botón de selección, el campo para el nombre exacto de la hoja y un aviso para verificarlo antes de subir el archivo.
2. PHP envía `file` y `sheet_name` juntos como `multipart/form-data` a `POST /excel/read`.
3. Se aceptan `.xlsx`, `.xlsm`, `.xls` y `.ods`; el frontend y la API limitan el archivo a 30 MB. La solicitud multipart tiene un timeout cURL mayor que las solicitudes JSON.
4. Cuando la API responde correctamente, la pantalla muestra el nombre de archivo, la hoja procesada, el total de filas y una vista previa de hasta 50 filas.
5. Si la API devuelve `422` con `available_sheets`, se muestra un modal con el nombre ingresado y las hojas disponibles.
6. El resultado o el error de selección de hoja se conserva en la sesión PHP solo para completar el redireccionamiento y mostrar esa respuesta. No constituye un historial de cargas.

La lectura no almacena el archivo ni los resultados. Para que el inicio muestre indicadores será necesario persistir los datos o exponer desde el backend una fuente agregada de resultados.

### Perfil

El formulario consulta los datos actuales del usuario y los actualiza con `PATCH /users/me`. El cambio de contraseña es opcional; si se envía, la API exige un mínimo de 12 caracteres.

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
