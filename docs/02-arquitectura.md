# Arquitectura y flujo de datos

## Estilo arquitectónico

La API usa un **monolito modular**. Seguridad y Excel comparten proceso, configuración y conexión a base de datos, pero cada módulo encapsula sus rutas y casos de uso. No hay comunicación de red entre módulos ni despliegues independientes.

```text
Uvicorn
└── app.create_app()
    └── api (ensambla los routers)
        ├── modules.security
        └── modules.excel
```

## Capas por módulo

| Capa | Responsabilidad |
|---|---|
| `routes.py` / `users/routes.py` | Adaptar HTTP, recibir entradas, invocar servicios y declarar respuestas. |
| `dtos/requests` | Validar y normalizar datos de entrada; limitar valores admitidos. |
| `dtos/responses` | Definir explícitamente el contrato que recibe el frontend. |
| `services` | Aplicar reglas de negocio y coordinar el caso de uso. |
| `repositories` | Consultar o persistir datos, o adaptar la lectura del libro Excel. |
| `entities` | Representar entidades persistentes o del dominio del módulo. |
| `migrations` | Versionar cambios de esquema de base de datos cuando corresponda. |

`modules/security/models.py`, `role.py` y `permission.py` se conservan como fachadas para imports antiguos; las definiciones canónicas están en `modules/security/entities/`.

## Componentes compartidos

- `app/`: construye la aplicación FastAPI y convierte errores esperados `ApplicationError` en respuestas HTTP.
- `api/`: registra los routers disponibles.
- `core/config.py`: carga `DB_*` y descifra usuario/contraseña cuando están cifrados con Fernet.
- `core/database.py`: crea el engine SQLAlchemy y las sesiones.
- `modules/security/database.py`: entrega una sesión por petición y la cierra al finalizar.

## Flujo de autenticación

1. `POST /auth/login` recibe `LoginRequest`.
2. `AuthService` normaliza el usuario y busca la cuenta por medio de `AccountRepository`.
3. La contraseña se verifica contra su hash PBKDF2-HMAC-SHA256.
4. Si es válida, el servicio genera un token opaco. `TokenRepository` guarda solamente su hash y vencimiento.
5. Se responde con `LoginResponse` y `UserResponse`; la respuesta no incluye el hash de contraseña.
6. En solicitudes protegidas, `CurrentAccount` extrae el Bearer token, compara su hash, comprueba revocación y vencimiento, y carga la cuenta activa. Las dependencias de permisos verifican las acciones permitidas.

## Flujo de usuarios

```text
HTTP request
  → DTO request
  → route
  → UserService (reglas/roles)
  → AccountRepository / TokenRepository
  → SQLAlchemy entities
  → DTO response
  → HTTP response
```

El servicio aplica los límites de rol y de cuenta propia, cifra las contraseñas mediante hash antes de persistir, confirma transacciones y convierte conflictos de unicidad en HTTP `409`.

## Flujo de Excel

`POST /excel/read` y `POST /excel/dashboard/import` tienen propósitos diferentes:

- **Lectura/previsualización:** `/excel/read` abre la hoja seleccionada y devuelve sus filas como JSON. No guarda el archivo ni los datos.
- **Dashboard persistente:** `/excel/dashboard/import` lee únicamente `BD GEN` y `TD PROGRAMAS`, normaliza las filas, persiste resultados y referencia dinámica, y activa una versión del conjunto de datos.

Ambos validan el rol y tamaño máximo de 30 MB y ejecutan el parseo fuera del event loop. Ninguno procesa macros o guarda el archivo binario.

## Flujo de importación persistente

```text
Instructor/superadmin
  → POST /excel/dashboard/import (Bearer + archivo)
  → validación de archivo y hojas requeridas
  → SHA-256 e idempotencia
  → lectura de BD GEN + referencia visible de TD PROGRAMAS
  → validación y normalización por fila
  → transacción: estudiantes/programas/resultados/referencias
  → cambio atómico de snapshot activo
  → respuesta con filtros, auditoría, métricas y página 1 (máximo 50 programas)
```

1. Se registra una importación `PROCESSING` con hash y datos de auditoría. Un hash ya conocido no crea una segunda carga. Si su importación fue desactivada, la API responde `409`; no la restaura automáticamente.
2. `DashboardWorkbookRepository` valida encabezados y extrae las dos hojas requeridas; `DashboardProcessor` convierte cada intento de origen en un registro listo para persistir.
3. La transacción inserta resultados con unicidad `(import_id, source_row_number)`, la referencia visible de `TD PROGRAMAS` y las dimensiones reutilizables de estudiante/programa.
4. `excel_dashboard_state` es una fila de coordinación bloqueada al activar: el snapshot anterior pasa a `HISTORICAL` y el nuevo a `ACTIVE` en el mismo commit. Si falla el procesamiento, el lote de resultados se revierte y la importación queda `FAILED`.
5. El servicio consulta la versión activa o histórica desde MySQL. No depende de una caché local de un worker, por lo que varios procesos pueden atender las lecturas.

El superadmin puede desactivar snapshots `ACTIVE`, `HISTORICAL` o `FAILED` mediante una marca `deleted_at`; no se borran sus filas. Al desactivar el activo, se limpia `active_import_id` y el dashboard queda sin snapshot activo hasta la siguiente importación. Las consultas normales ocultan los desactivados y el endpoint administrativo los presenta como `DELETED`. El instructor solo consulta el snapshot activo; el historial y la desactivación son exclusivos del superadmin.

El GLOBAL principal procede de la columna J original. El valor bruto y su versión numérica se conservan; valores no numéricos quedan nulos. E:I alimenta solo un cálculo alternativo y Q:U conserva los niveles fuente. Los nombres de programa se identifican por texto original, sin fusionar etiquetas por normalización.

`TD PROGRAMAS` es una tabla dinámica guardada en el libro. Se persiste la selección de año y los valores que están visibles al momento de importar; no se intenta recalcular la tabla dinámica ni se toma como reemplazo del histórico de `BD GEN`.

## Razones de esta construcción

- Los DTOs aíslan el contrato HTTP de las entidades ORM y evitan exponer campos internos.
- Los servicios permiten probar reglas de negocio sin pasar por HTTP.
- Los repositorios concentran el acceso a SQLAlchemy o al motor Excel.
- La separación por módulo reduce dependencias cruzadas y facilita agregar capacidades.
- El monolito modular evita el coste operativo de microservicios antes de necesitar escalado o despliegue independiente.
