# Seguridad y migraciones

## Contraseñas y sesiones

- Las contraseñas de cuentas se guardan con PBKDF2-HMAC-SHA256, salt aleatorio y 600 000 iteraciones. No se almacenan en texto claro.
- El login produce un token aleatorio opaco. En la tabla solo se conserva su hash SHA-256, vencimiento y estado de revocación.
- El token vence a las 8 horas. Logout y desactivación de cuenta revocan tokens.
- Las respuestas de usuario no incluyen contraseña ni hash.
- El acceso a endpoints protegidos usa `Authorization: Bearer <access_token>`.

## Roles

| Acción | Superadmin | Instructor | Estudiante |
|---|---:|---:|---:|
| Consultar/editar perfil propio | Sí | Sí | Sí |
| Consultar otros perfiles | Sí | Sí, excepto superadmins | No |
| Editar otros perfiles | Sí | Sí con restricciones | No |
| Crear instructor/estudiante | Sí | No | No |
| Desactivar cuentas | Sí | No | No |
| Leer Excel | Sí | Sí | No |

Un instructor no cambia usuario, rol ni contraseña de otras cuentas. Un estudiante solo administra su propio perfil y no cambia usuario ni rol. No se puede desactivar al último superadmin activo. No hay registro público ni endpoint público para crear o promover superadmins.

## Configuración secreta

`core/config.py` busca `APP_MASTER_KEY`. Si los valores de usuario o contraseña MySQL están cifrados en `core/.env`, Fernet los descifra al cargar configuración. La clave maestra debe recibirse por un canal seguro y exportarse localmente; nunca debe añadirse a Git o a los documentos.

Las variables `BOOTSTRAP_SUPERADMIN_*` se usan solo durante el aprovisionamiento inicial. Quitarlas de la terminal después del bootstrap no elimina la cuenta creada en MySQL.

## Migraciones activas

- `alembic.ini` apunta a `modules/security/migrations` y a sus revisiones versionadas.
- `0001_security_tables` crea `api_users`, `api_access_tokens` y sus índices.
- `0002_academic_dashboard` crea el esquema relacional de importaciones y resultados del dashboard, incluida la fila única de `excel_dashboard_state`.
- Alembic guarda la revisión aplicada en `alembic_version`.
- El servidor no migra ni crea tablas automáticamente; migrar es un paso operativo explícito.
- Se mantiene Alembic porque ya es el gestor de migraciones del backend; no se añade Liquibase en paralelo.

### Base nueva

1. Crear la base/schema MySQL por separado.
2. Ejecutar `python -m modules.security.bootstrap` desde `core/` con configuración y variables iniciales. El bootstrap aplica migraciones y crea el primer superadmin.
3. Iniciar Uvicorn.

### Aplicar migraciones

Ejecutar desde `core/`:

```powershell
..\venv\Scripts\python.exe -m modules.security.migrations
```

Ejecuta el comando antes de iniciar una versión nueva de la API. Para una instalación nueva, `modules.security.bootstrap` aplica las migraciones pendientes antes de crear la cuenta superadmin. Para una actualización, este comando aplica las revisiones nuevas sin volver a ejecutar el bootstrap.

Si existe una base legacy con las dos tablas de seguridad y sin historial Alembic, el servicio exige que coincidan con los modelos. Entonces marca `0001_security_tables` y continúa hacia `head`, que incluye `0002_academic_dashboard`. Si la seguridad está incompleta, difiere de los modelos o ya hay tablas académicas sin historial en esa base legacy, aborta sin marcarla. Un esquema académico sin las tablas legacy de seguridad no se adopta automáticamente: respáldalo y revísalo antes de migrar.

La importación registra contenido personal de estudiantes (documento, nombre, correo y filas fuente) en MySQL para habilitar búsquedas e historial. El Excel binario no se persiste. Restringe acceso a la base, copias de seguridad y snapshots de acuerdo con las políticas de datos de la institución; los logs HTTP no deben incluir payload ni datos personales.

### Reversión

El `downgrade` de `0002_academic_dashboard` elimina las tablas académicas y sus snapshots; el de `0001_security_tables` elimina usuarios y tokens. Son operaciones destructivas: requieren un respaldo verificado y aprobación operativa, y no deben usarse como mecanismo habitual para corregir una importación.
