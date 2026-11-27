# 034. Menú lateral con scroll y ventana de confirmación propia

**Fecha:** 26 de noviembre de 2026
**Fase:** interfaz
**Rama de código:** `dev` (commit `a914c58`)

## Por qué

- El superadmin tiene 11 opciones en el menú. En pantallas de poca altura la lista no cabía, el menú no hacía scroll y **"Cerrar sesión" quedaba fuera de la pantalla**.
- Las confirmaciones usaban la alerta del navegador ("localhost dice…"), que no deja mostrar datos ordenados ni diferenciar una acción de riesgo de una de recuperación.

## Qué cambió

**Menú lateral (`front/dashboard.css`)**

- La barra lateral mide lo mismo que la ventana (`100dvh`). **Solo la lista del menú hace scroll**, con una barra delgada; la marca queda arriba y la tarjeta de la cuenta con **Cerrar sesión** queda siempre visible abajo.
- En pantallas bajas (menos de 820 px y de 620 px de alto) el menú se compacta: menos margen y opciones más bajas.

**Ventana de confirmación**

| Archivo | Cambio |
|---|---|
| `front/dashboard.js` | `window.appConfirm(opciones)` crea la ventana y devuelve una promesa (`true` o `false`). |
| `front/partials/shared/js/confirm.js` (nuevo) | `confirmAction(opciones)` para los módulos ES; si `appConfirm` no está cargada, usa `window.confirm`. |
| `front/dashboard.css` | Estilos `.confirm-overlay`, `.confirm-dialog`, `.button-danger` y la versión móvil, con los botones a lo ancho. |

- **Opciones:** `title`, `message`, `details` (pares etiqueta/valor que se muestran en un recuadro), `confirmLabel`, `cancelLabel` y `tone`. `tone` es `danger` (botón rojo) o `primary` (botón verde).
- **Cierre:** Esc, un clic fuera o Cancelar cierran sin hacer nada. El foco queda dentro de la ventana; en las acciones de riesgo empieza en "Cancelar". Al cerrar, el foco vuelve a donde estaba.
- **Formularios PHP con `data-confirm`:** usan la ventana con los atributos opcionales `data-confirm-title`, `data-confirm-label` y `data-confirm-tone`.

Se usa en:

| Pantalla | Acciones |
|---|---|
| Cursos | Eliminar un curso (muestra curso, materia, nivel y estudiantes) y quitar a un estudiante. |
| Cursos eliminados | Habilitar (muestra además quién lo eliminó y cuándo). |
| Importaciones | Desactivar y restaurar (con el nombre del archivo). |
| Usuarios | Desactivar una cuenta. |

## Verificación

- Todos los imports de los módulos JS resuelven; `node --check dashboard.js` y `php -l` sin errores.
- En el navegador, con la cuenta de superadmin y una ventana de 520 px de alto: el menú hace scroll (300 de 401 px visibles) y "Cerrar sesión" sigue visible.
- La ventana roja (eliminar) y la verde (habilitar) se ven bien, el foco empieza en el botón correcto y Esc y Cancelar devuelven `false` sin ejecutar nada.
