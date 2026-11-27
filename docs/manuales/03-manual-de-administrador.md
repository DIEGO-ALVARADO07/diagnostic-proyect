# Manual de administrador

**Sistema:** Diagnóstico académico — comparación ESE + CORHUILA
**Para:** el superadmin (administración funcional) y quien opera el servidor
**Versión:** 27 de noviembre de 2026

El uso diario (Dashboard, ESE, CORHUILA, Estudiantes, Cursos) está en el [Manual de usuario](01-manual-de-usuario.md). Este manual cubre lo que **solo el administrador** hace.

---

## 1. Roles

| Rol | Puede |
|---|---|
| **superadmin** | Todo lo del instructor, y además: crear y desactivar cuentas, ver el historial de importaciones, desactivar y restaurar importaciones, ver los cursos eliminados y habilitarlos. |
| **instructor** | Importar ESE y CORHUILA; consultar el Dashboard, ESE y CORHUILA; asignar el programa a los "Sin programa"; ver estudiantes por nivel; crear cursos, agregarles estudiantes y eliminarlos (de forma lógica). |
| **estudiante** | Solo su perfil. El inicio de sesión de estudiantes todavía no forma parte del uso del sistema. |

**Menú del superadmin:** Dashboard, ESE, CORHUILA, Importar Excel, Estudiantes, Cursos, **Cursos eliminados**, **Importaciones**, **Usuarios**, **Crear cuenta** y Mi perfil.

**Principio de auditoría:** en este sistema **nada se borra**. Eliminar o desactivar deja el registro con **quién y cuándo**, y solo el superadmin lo recupera.

## 2. Cuentas de usuario

### Crear una cuenta

**Crear cuenta** → nombre completo, nombre de usuario, correo, **rol** (Instructor o Estudiante) y **contraseña inicial** (al menos 12 caracteres) → **Crear cuenta**.

- Entrega la contraseña inicial a la persona por un canal privado y pídele que la cambie en **Mi perfil**.
- No se pueden crear otros superadmin desde la pantalla. El primero se crea al instalar, con `tasks.ps1 bootstrap`.

### Ver y desactivar cuentas

**Usuarios** muestra las cuentas activas, con búsqueda y filtro por rol.

**Desactivar** pide confirmación. La persona pierde el acceso y sus sesiones se cierran. La cuenta se conserva.

## 3. Importaciones de Excel

**Importaciones** muestra **todas** las cargas, con su archivo, fecha, estado y filas.

| Estado | Significado |
|---|---|
| Activa | Es la que se consulta en su espacio: **ESE** tiene una sola activa (trae todo el histórico); **CORHUILA**, una por periodo. |
| Histórica | Se reemplazó por una carga más reciente del mismo espacio. |
| Fallida | El archivo no tenía la estructura esperada (hojas o columnas). No reemplazó a la activa. |
| Desactivada | Se ocultó a propósito. Debajo dice cuándo y por quién. |

### Desactivar

**Desactivar** (con confirmación) oculta la importación en todas las consultas, pero conserva sus datos.

Si desactivas la **activa**, esa prueba queda "a la espera del archivo" hasta que se suba otra o se restaure.

### Restaurar

**Restaurar** (con confirmación) quita la desactivación y guarda quién y cuándo:

- si su prueba y periodo **no tienen otra activa**, **vuelve a ser la activa**;
- si después se subió **otra más reciente**, queda como **histórica** y no reemplaza a la nueva;
- si era fallida, sigue fallida.

Si alguien intenta subir de nuevo un archivo desactivado, el sistema no lo permite y pide restaurarlo desde aquí.

## 4. Cursos eliminados

Los instructores pueden **eliminar** cursos, pero no recuperarlos. **Cursos eliminados** muestra una tabla con cada curso eliminado:

| Columna | Contenido |
|---|---|
| Curso | Materia y nombre. |
| Nivel | N1 a N4. |
| Descripción y Metodología | Tal como se crearon. |
| Estudiantes | Cuántos tenía inscritos (se conservan). |
| Creado | Quién y cuándo. |
| Eliminado | Quién y cuándo. |

**Habilitar** (con confirmación) devuelve el curso a su nivel **con los mismos estudiantes** y registra quién lo habilitó.

Mientras un curso está eliminado, nadie puede crear otro con el mismo nombre en ese nivel y materia: el sistema pide habilitarlo.

## 5. Calidad de los datos

### Estudiantes "Sin programa" (CORHUILA)

El Excel de CORHUILA casi nunca trae el documento. El sistema busca a cada estudiante en el histórico de ESE, en este orden:

1. por documento;
2. por **nombre completo** único (si hay homónimos, el correo desempata);
3. por correo.

Con eso toma el programa de su registro de ESE más reciente. Los que no aparecen quedan **"Sin programa"**:

- en el módulo **CORHUILA**, asígnales el programa a mano. Esa asignación **manda sobre ESE**;
- **Recalcular cruce** vuelve a buscar a todos. Hazlo después de subir un ESE nuevo.

### Avisos conocidos

- Los códigos `N`, `N/A` y `P` en los puntajes se tratan como "sin puntaje" y se informan en la auditoría de la importación.
- Algunos nombres de simulacros de ESE traen un espacio al final; el sistema los reconoce igual.

## 6. Mantenimiento del servidor

Estos comandos se ejecutan en PowerShell desde `back\api-reader-excel`.

| Comando | Para qué |
|---|---|
| `.\tasks.ps1 run` | Arrancar la API. |
| `.\tasks.ps1 migrate` | Aplicar las migraciones de una versión nueva. Saca antes un respaldo. |
| `.\tasks.ps1 test` | Comprobar que todo funciona: 146 pruebas, sin tocar la base real. |
| `.\tasks.ps1 backup -Label <nombre>` | Respaldo manual. |
| `.\tasks.ps1 backup-daily` | Respaldo solo si hubo cambios. |
| `.\tasks.ps1 schedule-backup -At 02:30` | Programar el respaldo diario. |
| `.\tasks.ps1 unschedule-backup` | Quitar la tarea programada. |
| `.\tasks.ps1 reset` | Vaciar la base para empezar desde cero. |

## 7. Respaldos

Las copias se guardan en `C:\Users\<usuario>\respaldos\excel_reader`, **fuera del repositorio**. Contienen datos personales: guárdalas con cuidado y no las compartas.

### Respaldo manual

```powershell
.\tasks.ps1 backup -Label antes-0011
```

Hazlo **siempre** antes de una migración o de un cambio grande.

### Respaldo diario automático

```powershell
.\tasks.ps1 schedule-backup -At 02:30
```

- **Solo guarda copia si los datos cambiaron.** Si nadie subió un Excel ni cambió cursos, programas o cuentas, no crea archivo, para no llenar el disco. Iniciar sesión no cuenta como cambio.
- **Cuándo corre:** con tu usuario, todos los días a la hora indicada. Si el equipo estaba apagado, corre al encenderlo. Si MySQL estaba apagado, reintenta cada hora hasta 6 veces.
- **Registro:** cada ejecución queda en `C:\Users\<usuario>\respaldos\respaldo-diario.log`.
- **Probarla:** Programador de tareas → "Diagnostico academico - respaldo diario" → **Ejecutar**, y luego revisa el registro.
- **Conservar solo las últimas copias:** `.\tasks.ps1 schedule-backup -At 02:30 -Keep 30` deja las 30 copias diarias más recientes. Las manuales (`antes-…`) nunca se borran.

### Restaurar un respaldo

1. Detén la API (`Ctrl+C`).
2. En HeidiSQL: *Archivo → Ejecutar archivo SQL* → elige el `.sql`. La base vuelve **exactamente** al estado de esa copia.
3. Ejecuta `.\tasks.ps1 migrate`, por si la copia es de una versión anterior.
4. Arranca la API (`.\tasks.ps1 run`).

## 8. Vaciar la base (demostraciones)

Para mostrar el recorrido completo desde una base vacía:

```powershell
.\tasks.ps1 reset
```

1. Primero se hace un respaldo `antes-vaciar`. **Si el respaldo falla, no se borra nada.**
2. Te pide escribir el nombre de la base (`excel_reader`) para confirmar.
3. Borra todos los datos académicos: importaciones, resultados, estudiantes, programas, cursos e inscripciones.
4. **Conserva las cuentas**, para que puedas entrar y empezar por **Importar Excel**.
5. Reinicia la API (`.\tasks.ps1 run`), porque guarda datos en memoria.

Para volver al estado anterior, restaura la copia `…_antes-vaciar.sql`.

`.\tasks.ps1 reset -IncludeUsers` también borra las cuentas; después hay que crear el superadmin con `.\tasks.ps1 bootstrap`.

## 9. Seguridad

- **`core\.env` y `APP_MASTER_KEY`** no van en Git, ni por correo o chat. Entrégalos por un canal privado.
- **Contraseñas:** al menos 12 caracteres. El sistema nunca muestra ni devuelve las contraseñas.
- **Sesiones:** duran 8 horas. Al desactivar una cuenta, sus sesiones se cierran.
- **Pendiente conocido:** "Cerrar sesión" cierra la sesión del navegador, pero el token de la API sigue válido hasta que vence (8 horas). Está planificado en la fase 6, junto con el límite de intentos de login y la limpieza de tokens vencidos.
- **Datos personales:** la base y los respaldos tienen nombres, documentos y correos de estudiantes. Protégelos según las políticas de la institución.

## 10. Rutina recomendada

| Cuándo | Qué revisar |
|---|---|
| Cada periodo | Subir ESE (que trae el histórico) y el CORHUILA del periodo. Revisar "Sin programa" y pulsar "Recalcular cruce". |
| Cada semana | Que existan las copias `…_diario.sql` de los días con cambios, y el registro `respaldo-diario.log`. |
| Antes de actualizar | `.\tasks.ps1 backup -Label antes-actualizar`, luego `git pull`, `install` y `migrate`. |
| Cuando alguien se va | Desactivar su cuenta en **Usuarios**. |
