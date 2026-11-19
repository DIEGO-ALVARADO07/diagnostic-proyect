# 🔐 Guía de Seguridad y Gestión de Entornos (FastAPI)

Este documento explica cómo funciona el cifrado de credenciales en nuestro proyecto y el flujo de trabajo para cada miembro del equipo de desarrollo.

---

## 1. ¿Cómo funciona la seguridad del proyecto?

Para evitar que las contraseñas reales de la base de datos queden expuestas en el código o en Git, utilizamos **cifrado simétrico (Fernet)** combinado con **Pydantic Settings**:

* **Archivo `.env.dev` (La caja cerrada):** Contiene las variables de entorno con los datos sensibles encriptados (cadenas que empiezan por `gAAAAAB...`). Es seguro compartirlo o mantenerlo en el repositorio.
* **Llave Maestra (`APP_MASTER_KEY`):** Es la clave única necesaria para descifrar el contenido del `.env.dev`. **Nunca** se guarda dentro de los archivos del proyecto; se carga temporalmente en la terminal al iniciar el servidor.
* **Módulo `src/core/config.py` (El guardia):** Al arrancar FastAPI, lee el `.env.dev`, toma la llave maestra de la terminal, descifra las credenciales únicamente en memoria RAM y establece la conexión con MySQL.

---

## 2. Roles y Permisos en el Equipo

El acceso a los datos está dividido por niveles de responsabilidad bajo el principio de **mínimo privilegio**:

| Rol | Archivo de Entorno | Permisos en Base de Datos |
| :--- | :--- | :--- |
| **Desarrolladores** | `.env.dev` + `APP_MASTER_KEY_DEV` | Acceso exclusivo a la BD de desarrollo (`SELECT`, `INSERT`, `UPDATE`, `DELETE`). Sin permisos administrativos (`DROP` o `GRANT`). |
| **Líderes / QA** | `.env.staging` + `APP_MASTER_KEY_STAGING` | Acceso a entorno de pruebas / pre-producción. |
| **Administrador** | `.env.prod` + `APP_MASTER_KEY_PROD` | Control total sobre infraestructura y base de datos de producción. |

> **Nota para desarrolladores:** No necesitan ejecutar ningún script de encriptación ni crear usuarios en MySQL. Solo deben usar el archivo `.env.dev` y la llave entregada por el administrador.

---

## 3. Pasos para levantar el proyecto (Equipo de Desarrollo)

1. **Clonar el repositorio** y activar el entorno virtual de Python:
   ```bash
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1

   # Linux / Mac
   source venv/bin/activate
   ```

2. **Asegurar el archivo de entorno:**
   Verifica que el archivo `.env` (o `.env.dev` renombrado a `.env`) esté en la raíz del proyecto.

3. **Cargar la Llave Maestra en la terminal actual:**
   *(Solicita la `APP_MASTER_KEY_DEV` al administrador del proyecto por canal privado).*

   * **En Windows (PowerShell):**
     ```powershell
     \$env:APP_MASTER_KEY="PEGA_AQUI_LA_LLAVE_MAESTRA"
     ```
   * **En Linux / Mac:**
     ```bash
     export APP_MASTER_KEY="PEGA_AQUI_LA_LLAVE_MAESTRA"
     ```

4. **Iniciar el servidor de FastAPI:**
   ```bash
   uvicorn src:app --reload
   ```

---

## 4. Reglas Obligatorias de Seguridad

* ❌ **Nunca** subas la `APP_MASTER_KEY` a GitHub, GitLab ni la escribas dentro del código fuente.
* ❌ **Nunca** compartas la llave maestra por el mismo canal donde se aloja el código.
* ✅ Si la llave maestra llega a filtrarse, repórtalo de inmediato para rotar las credenciales y generar un nuevo `.env` cifrado.
