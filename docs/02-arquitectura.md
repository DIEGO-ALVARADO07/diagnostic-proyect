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

1. La ruta autentica la solicitud, valida rol y extensión y limita la lectura a 30 MB más un byte de control.
2. Construye el DTO interno `ReadWorkbookRequest`.
3. `ExcelService` valida reglas de carga y traslada el procesamiento síncrono a un thread pool para no bloquear el event loop.
4. `WorkbookRepository` usa fastexcel para abrir el libro y Polars para convertir la hoja seleccionada a filas Python.
5. La entidad `WorkbookRead` representa el resultado interno y `ReadWorkbookResponse` define la respuesta JSON.
6. El Excel y las filas no se guardan en la base de datos.

El repositorio registra tiempos de apertura, conversión, materialización de filas y duración de la respuesta HTTP sin registrar contenido del archivo.

## Razones de esta construcción

- Los DTOs aíslan el contrato HTTP de las entidades ORM y evitan exponer campos internos.
- Los servicios permiten probar reglas de negocio sin pasar por HTTP.
- Los repositorios concentran el acceso a SQLAlchemy o al motor Excel.
- La separación por módulo reduce dependencias cruzadas y facilita agregar capacidades.
- El monolito modular evita el coste operativo de microservicios antes de necesitar escalado o despliegue independiente.
