# Seguridad y migraciones

## Contraseñas y sesiones

- Las contraseñas de cuentas se guardan con PBKDF2-HMAC-SHA256, salt aleatorio y 600 000 iteraciones. No se almacenan en texto claro.
- El login produce un token aleatorio opaco. En la tabla solo se conserva su hash SHA-256, vencimiento y estado de revocación.
- El token vence a las 8 horas. Logout y desactivación de cuenta revocan tokens.
- Las respuestas de usuario no incluyen contraseña ni hash.
- El acceso a endpoints protegidos usa `Authorization: Bearer <access_token>`. Sin token o con uno inválido o vencido, la API responde `401` con la cabecera `WWW-Authenticate: Bearer`; sin permisos, `403`.

## Roles

| Acción | Superadmin | Instructor | Estudiante |
|---|---:|---:|---:|
| Consultar/editar perfil propio | Sí | Sí | Sí |
| Consultar otros perfiles | Sí | Sí, excepto superadmins | No |
| Editar otros perfiles | Sí | Sí con restricciones | No |
| Crear instructor/estudiante | Sí | No | No |
| Desactivar cuentas | Sí | No | No |
| Leer Excel | Sí | Sí | No |
| Importar snapshot académico | Sí | Sí | No |
| Consultar historial o desactivar snapshots | Sí | No | No |
| Subir y consultar matriculados (datos personales) | Sí | No | No |

Un instructor no cambia usuario, rol ni contraseña de otras cuentas. Un estudiante solo administra su propio perfil y no cambia usuario ni rol. No se puede desactivar al último superadmin activo. No hay registro público ni endpoint público para crear o promover superadmins.

## Configuración secreta

`core/.env` **no se versiona** (lo excluye el `.gitignore`; la plantilla es `core/.env.example`). `core/config.py` busca `APP_MASTER_KEY`. Si los valores de usuario o contraseña MySQL están cifrados en `core/.env`, Fernet los descifra al cargar configuración. La clave maestra debe recibirse por un canal seguro y exportarse localmente; nunca debe añadirse a Git o a los documentos.

Las variables `BOOTSTRAP_SUPERADMIN_*` se usan solo durante el aprovisionamiento inicial. Quitarlas de la terminal después del bootstrap no elimina la cuenta creada en MySQL.

## Migraciones activas

- Las migraciones viven en `back/api-reader-excel/migrations/` (antes en `modules/security/migrations/`; las revisiones no cambiaron, así que las bases existentes siguen siendo válidas). `alembic.ini` apunta a esa carpeta.
- Todos los modelos (seguridad y académicos) comparten la base declarativa `core.orm.Base`.
- Alembic guarda la revisión aplicada en `alembic_version`.
- El servidor no migra ni crea tablas automáticamente: migrar es un paso operativo explícito.

| Revisión | Contenido |
|---|---|
| `0001_security_tables` | `api_users`, `api_access_tokens` y sus índices. |
| `0002_academic_dashboard` | Esquema del dashboard: importaciones, estudiantes, programas, alias, resultados, referencia de `TD PROGRAMAS` y la fila única `excel_dashboard_state`. |
| `0003_soft_delete_excel_imports` | `excel_imports.deleted_at` para desactivación lógica. |
| `0004_unify_programs` | Fusiona programas cuyo nombre solo difiere en tildes, mayúsculas o espacios: conserva el de menor id, reasigna resultados y alias, guarda cada nombre como alias y hace **único** `academic_programs.normalized_key`. |
| `0005`–`0011` | Prueba, periodo y momento; identidad por correo y luego por documento; programa manual; cursos y auditoría de eliminar y restaurar. Detalle en [Instalación y operación](03-instalacion-y-operacion.md). |
| `0012_enrollment_records` | Tablas de matriculados: `enrollment_uploads` (una carga activa por periodo) y `enrollment_records` (una fila por estudiante y programa, con todas las columnas del archivo). |
| `0013_enrollment_matching` | `academic_students.document_type` y la tabla `academic_result_programs` (los programas extra de un resultado, para el doble programa). |

### Base nueva

1. Crear la base/schema MySQL por separado.
2. `.\tasks.ps1 bootstrap` desde `back/api-reader-excel`: aplica las migraciones y crea el primer superadmin.
3. `.\tasks.ps1 run`.

### Aplicar migraciones en una base existente

```powershell
$env:APP_MASTER_KEY = "<clave>"   # si core\.env va cifrado
.\tasks.ps1 migrate               # equivale a: python -m migrations
```

Ejecútalo antes de arrancar una versión nueva de la API. No ejecutes el bootstrap solo para migrar, y no uses `alembic upgrade head` directamente: el comando del proyecto valida antes las bases antiguas.

Si existe una base legacy con las dos tablas de seguridad y sin historial Alembic, el servicio (`migrations/runner.py`, `DatabaseMigrationService`) exige que coincidan con los modelos. Entonces marca `0001_security_tables` y continúa hasta la última revisión. Si la seguridad está incompleta, difiere de los modelos o ya hay tablas académicas sin historial en esa base legacy, aborta sin marcarla. Un esquema académico sin las tablas legacy de seguridad no se adopta automáticamente: respáldalo y revísalo antes de migrar.

**Antes de `0004` haz una copia de seguridad**: fusiona datos. En MySQL los cambios de índice confirman la transacción de forma implícita; si fallara la creación del índice único, la fusión ya estaría aplicada (es correcta por sí misma) y basta con revisar el error y reintentar.

La importación registra contenido personal de estudiantes (documento, nombre, correo y filas fuente) en MySQL para habilitar búsquedas e historial. El archivo de **matriculados** guarda además teléfonos, género, estrato y fecha de nacimiento: la API solo los entrega al superadmin (`/enrollment/*`) y el resto de pantallas solo reciben el programa, el semestre y el tipo y número de documento. El Excel binario no se persiste. Restringe el acceso a la base, las copias de seguridad y los snapshots de acuerdo con las políticas de datos de la institución; los logs no incluyen payload ni datos personales.

### Reversión

| Revisión | Efecto del `downgrade` |
|---|---|
| `0013_enrollment_matching` | Quita el tipo de documento y los programas extra: el doble programa deja de contar en el segundo programa. |
| `0012_enrollment_records` | Elimina las tablas de matriculados y sus cargas. |
| `0004_unify_programs` | Solo vuelve al índice no único. **No separa** los programas fusionados (cada resultado conserva su `program_name_raw`). |
| `0003_soft_delete_excel_imports` | Quita `deleted_at`: los registros desactivados dejan de estar marcados y podrían volver a aparecer. |
| `0002_academic_dashboard` | Elimina las tablas académicas y sus snapshots. |
| `0001_security_tables` | Elimina usuarios y tokens. |

Son operaciones destructivas: requieren una copia verificada y aprobación operativa, y no deben usarse para corregir una importación.
