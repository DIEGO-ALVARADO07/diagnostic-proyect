# Frontend PHP

> Actualizado el 27 de noviembre de 2026 (rama `dev`, commit `543d7fb`).

## Propósito

Interfaz web para que el instructor y el superadmin carguen los Excel de ESE y CORHUILA, comparen resultados, revisen a los estudiantes por nivel y armen cursos por nivel y materia. El superadmin sube además el archivo de matriculados de cada periodo.

- Está hecha en **PHP**, que pinta cada pantalla en el servidor, y en **JavaScript con módulos ES nativos** (`type="module"`), que pide los datos a la API.
- **No necesita** Node.js, npm ni compilación.

## Estructura

| Ruta | Responsabilidad |
|---|---|
| `front/index.php` | Verifica la sesión, consulta el perfil, arma el menú según el rol, valida la vista pedida (`?view=`) y carga su pantalla, su CSS y su JS. Procesa los formularios de cuentas, carga de Excel e importaciones. Define `periodosDeCarga()`. |
| `front/api_client.php` | Sesión PHP (8 horas, cookie `HttpOnly` y `SameSite=Lax`), token Bearer y llamadas cURL (JSON y multipart). Define `API_BASE_URL`. |
| `front/login.php`, `front/logout.php` | Inicio y cierre de sesión. |
| `front/dashboard.css` | Estilos globales: colores, barra lateral con scroll, botones, tablas, ventana de confirmación y versión móvil. |
| `front/dashboard.js` | Búsqueda en tablas, menú móvil, la ventana de confirmación `window.appConfirm` y los formularios con `data-confirm`. |
| `front/partials/shared/` | Lo que comparten varias pantallas (tabla siguiente). |
| `front/partials/<módulo>/` | `screen.php` (plantilla), `style.css` y, si la pantalla consulta datos, `js/main.js`. |

Contenido de `front/partials/shared/`:

| Archivo | Para qué |
|---|---|
| `data.php` | **Proxy** de mismo origen hacia la API: valida los parámetros, adjunta el token y pide el token CSRF en los cambios (POST). |
| `style.css` | Tarjetas y gráficas. |
| `compare-side.php` y `js/compare-side.js` | Plantilla de una mitad del comparativo. Con la opción `onOpenProgram`, el nombre de cada programa es un botón (lo usa CORHUILA). |
| `js/api.js` | `apiRequest` (consultas) y `apiPost` (cambios con CSRF). |
| `js/dom.js` y `js/format.js` | Ayudas de pantalla y de formato de números. |
| `js/periods.js` | Año y periodo del año para los filtros. |
| `js/confirm.js` | `confirmAction`, la confirmación que usan los módulos ES. |
| `js/charts/` | Gráficas SVG. |

## Módulos de pantalla

| Vista (`?view=`) | Carpeta | Función |
|---|---|---|
| `enrollment` | `enrollment/` | **Solo superadmin; primera opción de su menú.** Carga del archivo de matriculados por periodo (el actual o el anterior), tarjetas con las cargas y la lista completa con filtros (periodo, programa, semestre, tipo de documento, género y estrato) y búsqueda. |
| `dashboard` | `dashboard/` | **Inicio.** ESE y CORHUILA lado a lado en un periodo. Filtros en cascada Año → Periodo → Momento (solo ESE) → Programa, que arrancan en el último periodo. Abajo, el programa y la competencia más bajos en común. "Ver módulo" abre ESE o CORHUILA con los mismos filtros. |
| `ese` | `ese/` | **Histórico de ESE.** Filtros Año → Periodo (o "Todo el año") → Momento y Asignatura. Tarjetas de programas, vista de programa y vista de estudiante. |
| `corhuila` | `corhuila/` | Resultados de CORHUILA por periodo. Filtros de periodo, programa y semestre, y búsqueda por nombre, documento, correo o programa. Pulsar un programa abre su detalle (indicadores, gráfica y estudiantes). Tabla de estudiantes de 25 en 25 con nivel y puntajes, y lista **"Sin programa"** con asignación manual y "Recalcular cruce". |
| `report` | `report/` | **Importar Excel:** prueba (ESE o CORHUILA), periodo (solo el actual o el anterior) y archivo. |
| `students` | `students/` | **Estudiantes de los Excel** en 5 grupos: N1–N4 y Sin resultado. Filtro Año → Periodo (o "Todo el histórico"), búsqueda y programa. Elegir un nivel no cambia el periodo. El documento se muestra con su tipo (`C 1075…`) y quien tiene doble programa aparece una vez por programa. |
| `courses` | `courses/` | **Cursos:** Nivel → Curso (materia, nombre, descripción y metodología) → Estudiantes. "Agregar estudiantes" inscribe en bloque por el nivel en la materia; también "Ver estudiantes" (con "Quitar") y "Eliminar" (lógico). |
| `courses_deleted` | `courses_deleted/` | **Solo superadmin.** Tabla de cursos eliminados con toda su información y el botón "Habilitar". |
| `imports` | `imports/` | **Solo superadmin.** Historial de importaciones con su auditoría. Permite desactivar y restaurar. |
| `users` | `users/` | **Solo superadmin.** Cuentas activas, con búsqueda, filtro por rol y desactivación. |
| `create_user` | `create_user/` | **Solo superadmin.** Crear cuentas de instructor o estudiante. |
| `profile` | `profile/` | Perfil propio y cambio de contraseña. |

## Navegación y permisos

El menú y la lista de vistas permitidas se arman en `index.php` según el rol. Al iniciar sesión se abre el Dashboard. Si se pide una vista que no está en el menú del rol, se abre la **primera opción** de su menú.

| Rol | Menú |
|---|---|
| `superadmin` | Matriculados, Dashboard, ESE, CORHUILA, Importar Excel, Estudiantes, Cursos, Cursos eliminados, Importaciones, Usuarios, Crear cuenta y Mi perfil. |
| `instructor` | Dashboard, ESE, CORHUILA, Importar Excel, Estudiantes, Cursos y Mi perfil. |
| `estudiante` | Mi perfil. |

**La API es la autoridad de los permisos:** ocultar una opción en PHP no reemplaza la autorización del backend. Por ejemplo, `course_restore`, `courses_deleted` y `enrollment` se rechazan en el proxy para quien no es superadmin, y la API también lo exige.

## Flujo de datos

1. `login.php` envía las credenciales a `POST /auth/login`. PHP regenera la sesión y guarda el token y el usuario **en el servidor**, nunca en `localStorage`.
2. Cada visita a `index.php` consulta `GET /users/me` para el rol y el menú.
3. Las pantallas con datos (Matriculados, Dashboard, ESE, CORHUILA, Estudiantes, Cursos y Cursos eliminados) cargan su `js/main.js`.
   - Ese JS llama a `partials/shared/data.php?resource=…`, que valida y reenvía a la API con el token.
   - Si la API responde `401`, se cierra la sesión y se vuelve al login.
4. Los cambios hechos desde JS (asignar programa, recalcular, crear, eliminar o habilitar un curso, inscribir, quitar estudiante) son POST al proxy con el encabezado `X-CSRF-Token`.
5. Los formularios PHP (subir Excel, subir matriculados, crear o desactivar cuentas, desactivar o restaurar importaciones) llevan `csrf_token` y los procesa `index.php`.
6. Los filtros se reflejan en la URL (`history.replaceState`), así que recargar la página o compartir el enlace conserva el periodo, el nivel y el programa. En CORHUILA, entrar o salir de un programa usa `history.pushState`, así que **Atrás** del navegador vuelve a la vista anterior.

## Confirmaciones

Las acciones de riesgo (eliminar, desactivar) y las de recuperación (habilitar, restaurar) se confirman con la **ventana propia** `window.appConfirm` (`dashboard.js`), no con la alerta del navegador.

- Muestra un título, la explicación y un recuadro con los datos.
- El botón es rojo (`danger`) para eliminar o desactivar, y verde (`primary`) para habilitar o restaurar.
- Esc, un clic fuera o Cancelar la cierran sin hacer nada.

| Desde | Cómo se usa |
|---|---|
| Módulos ES | `confirmAction(...)`, de `shared/js/confirm.js`. |
| Formularios PHP | `data-confirm`, más `data-confirm-title`, `data-confirm-label` y `data-confirm-tone`, todos opcionales. |

## Sesiones y seguridad

- La sesión PHP dura 8 horas, igual que el token. La cookie es `HttpOnly` y `SameSite=Lax`.
- Hay un token CSRF por sesión en los formularios y en los POST del proxy.
- El proxy valida los formatos (periodo, nivel, ids y largo de los textos) antes de llamar a la API.
- **Pendiente conocido:** `logout.php` cierra la sesión PHP pero no llama a `POST /auth/logout`. El token sigue válido en la API hasta que vence. Está anotado para la fase 6.

## Requisitos y ejecución local

- PHP 7.4 o posterior con cURL.
- La API debe estar en `http://127.0.0.1:8000`, que es el valor de `API_BASE_URL` en `front/api_client.php`. Cámbialo si usas otro host o puerto.
- Desde la **raíz del repositorio** (la carpeta que contiene `front/`):

```powershell
php -S 127.0.0.1:8081 -t .
```

Abre `http://127.0.0.1:8081/front/login.php`. En Apache/Laragon usa la raíz del repositorio como *document root*.

Para subir archivos de hasta 30 MB, ajusta `php.ini` y reinicia el servidor web:

```ini
upload_max_filesize = 30M
post_max_size = 32M
```

## Comprobación local

```powershell
Get-ChildItem .\front -Recurse -Filter *.php | ForEach-Object { php -l $_.FullName }
```

```powershell
node --check .\front\dashboard.js
```

La prueba funcional necesita la API encendida, una cuenta activa y una sesión iniciada en `front/login.php`.
