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
- Alembic guarda la revisión aplicada en `alembic_version`.
- Excel es sin estado, por lo tanto no tiene revisiones de esquema.
- El servidor no migra ni crea tablas automáticamente; migrar es un paso operativo explícito.

### Base nueva

1. Crear la base/schema MySQL por separado.
2. Ejecutar `python -m modules.security.bootstrap` desde `core/` con configuración y variables iniciales. El bootstrap aplica migraciones y crea el primer superadmin.
3. Iniciar Uvicorn.

### Aplicar una migración futura

Ejecutar desde `core/`:

```powershell
..\venv\Scripts\python.exe -m modules.security.migrations
```

La migración se aplica antes de iniciar la nueva versión de la API. Si se encuentra una base sin versión Alembic pero con ambas tablas de seguridad, el proceso compara sus columnas e índices con los modelos y solo la marca como inicializada cuando coinciden. Si falta una tabla o el esquema difiere, aborta sin marcar la revisión.

### Reversión

El `downgrade` de la primera revisión elimina `api_access_tokens` y `api_users`. Es una operación destructiva y no debe ejecutarse sobre datos que se necesiten conservar; requiere respaldo y una decisión operativa explícita.
