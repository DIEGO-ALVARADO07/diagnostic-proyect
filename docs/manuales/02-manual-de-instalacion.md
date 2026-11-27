# Manual de instalación

**Sistema:** Diagnóstico académico — comparación ESE + CORHUILA
**Para:** quien instala el sistema en un equipo o servidor Windows
**Versión:** 27 de noviembre de 2026 (rama `dev`, commit `543d7fb`)

Este manual lleva desde un equipo vacío hasta el sistema funcionando. Todos los comandos son de **PowerShell**. La versión técnica, con todos los detalles, está en [Instalación, uso y operación](../03-instalacion-y-operacion.md).

---

## 1. Requisitos

| Componente | Detalle |
|---|---|
| Windows 10/11 con PowerShell | PowerShell 5.1 o 7. |
| Git | Para descargar el código. |
| Python | El entorno probado usa Python 3.15. Instálalo y marca "Add to PATH". |
| MySQL 8 | Con una base **ya creada** (por ejemplo `excel_reader`) y un usuario con permisos para crear tablas e índices. Recomendado: **Laragon**, que incluye MySQL, PHP y HeidiSQL. |
| PHP 7.4 o posterior con cURL | Para el frontend; Laragon lo incluye. |
| Archivo `core/.env` | Lo entrega el administrador por un canal privado. |
| Clave `APP_MASTER_KEY` | Solo si `core/.env` trae las credenciales cifradas. También la entrega el administrador por un canal privado. |

> **Seguridad:** `core/.env`, la clave maestra y los respaldos de la base **nunca** se suben a Git ni se envían por correo o chat.

## 2. Descargar el código

```powershell
git clone https://github.com/DIEGO-ALVARADO07/diagnostic-proyect.git
```
```powershell
Set-Location diagnostic-proyect
```
```powershell
git switch dev
```
```powershell
Set-Location back\api-reader-excel
```

Si PowerShell no deja ejecutar `tasks.ps1` ("la ejecución de scripts está deshabilitada"), permítelo una vez para tu usuario:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Instalar dependencias

Desde `back\api-reader-excel`:

```powershell
.\tasks.ps1 install
```

Crea el entorno `venv\` e instala las librerías de `requirements.txt`.

## 4. Configurar la conexión

1. Copia el archivo `core\.env` que te entregaron en `back\api-reader-excel\core\`. Si vas a crear uno nuevo, parte de la plantilla:

   ```powershell
   Copy-Item core\.env.example core\.env
   ```

   Debe tener `DB_USER`, `DB_PASSWORD`, `DB_HOST` (por ejemplo `127.0.0.1`), `DB_PORT` (`3306`) y `DB_NAME` (`excel_reader`).

2. Si las credenciales van cifradas (empiezan por `gAAAAAB`), guarda la clave maestra **en las variables de entorno de tu usuario**. Así sirve en todas las terminales y en el respaldo automático:
   - Windows → "Editar las variables de entorno de esta cuenta" → **Nueva** → nombre `APP_MASTER_KEY` y el valor que te entregaron.
   - Cierra y vuelve a abrir PowerShell.

## 5. Crear las tablas y el primer administrador

**Solo la primera vez**, con la base vacía:

```powershell
.\tasks.ps1 bootstrap
```

Pide el usuario, el correo, el nombre completo y la contraseña del **superadmin**. La contraseña no se ve al escribirla y debe tener al menos 12 caracteres. El comando aplica todas las migraciones (`0001` a `0013`) y crea la cuenta. Debe terminar con `Cuenta superadmin inicial creada.`

**Si en cambio traes los datos de otro equipo**, restaura un respaldo `.sql` en HeidiSQL (*Archivo → Ejecutar archivo SQL*) y después ejecuta:

```powershell
.\tasks.ps1 migrate
```

## 6. Arrancar la API

```powershell
.\tasks.ps1 run
```

- Comprueba que `http://127.0.0.1:8000/health` responde `{"status":"ok"}`.
- La documentación interactiva de la API está en `http://127.0.0.1:8000/docs`.
- Deja esa terminal abierta; `Ctrl+C` la detiene.

## 7. Arrancar el frontend

En **otra** terminal, desde la **raíz del repositorio** (la carpeta `diagnostic-proyect`, que contiene `front\`):

```powershell
php -S 127.0.0.1:8081 -t .
```

Abre `http://127.0.0.1:8081/front/login.php` y entra con el superadmin.

- **Con Laragon/Apache:** usa la raíz del repositorio como *document root*.
- **Si la API usa otro host o puerto:** cambia `API_BASE_URL` en `front\api_client.php`.
- **Para subir archivos de hasta 30 MB**, en el `php.ini`:

  ```ini
  upload_max_filesize = 30M
  post_max_size = 32M
  ```

## 8. Programar el respaldo diario (recomendado)

Desde `back\api-reader-excel`:

```powershell
.\tasks.ps1 schedule-backup -At 02:30
```

Crea en Windows la tarea **"Diagnostico academico - respaldo diario"**:
- solo guarda copia si los datos cambiaron;
- si MySQL está apagado, reintenta cada hora hasta 6 veces.

Las copias quedan en `C:\Users\<usuario>\respaldos\excel_reader`. Detalle en el [Manual de administrador](03-manual-de-administrador.md#7-respaldos).

## 9. Comprobar la instalación

| Comprobación | Resultado esperado |
|---|---|
| `.\tasks.ps1 test` | `OK` (167 pruebas). |
| `http://127.0.0.1:8000/health` | `{"status":"ok"}` |
| Entrar con el superadmin | Se ve el Dashboard y el menú completo, que empieza por **Matriculados**. |
| Subir un Excel de ESE en Importar Excel | El Dashboard muestra la mitad de ESE. |

## 10. Actualizar a una versión nueva

1. Saca una copia de seguridad: `.\tasks.ps1 backup -Label antes-actualizar`
2. Trae el código: `git pull` en la rama `dev`.
3. Actualiza las librerías: `.\tasks.ps1 install`
4. Aplica las migraciones: `.\tasks.ps1 migrate`
5. Arranca de nuevo: `.\tasks.ps1 run`

El servidor **nunca** crea ni modifica tablas por su cuenta: siempre usa `migrate`.

## 11. Uso diario (después de instalar)

1. Enciende Laragon (MySQL).
2. En `back\api-reader-excel`, ejecuta `.\tasks.ps1 run`.
3. Arranca el frontend (Apache de Laragon o `php -S 127.0.0.1:8081 -t .`).
4. Entra a `http://127.0.0.1:8081/front/login.php`.

## 12. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `core\.env tiene credenciales cifradas. Define APP_MASTER_KEY…` | Falta la clave maestra. Agrégala a las variables de entorno de tu usuario (paso 4) y abre otra terminal. |
| `Falta core\.env…` | Copia el archivo `core\.env` a `back\api-reader-excel\core\`. |
| `No existe el venv…` | Ejecuta `.\tasks.ps1 install`. |
| PowerShell no deja ejecutar `tasks.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `/health` responde, pero las pantallas dan error | MySQL está apagado o las credenciales no son correctas. Revisa Laragon y `core\.env`. |
| El login dice que la API no está disponible | La API no está corriendo (paso 6) o `API_BASE_URL` apunta a otro lugar. |
| No se puede subir un Excel grande | Ajusta `upload_max_filesize` y `post_max_size` en `php.ini` (paso 7). |
| El puerto 8000 está ocupado | Usa `.\tasks.ps1 run -Port 8001` y cambia `API_BASE_URL`. |
