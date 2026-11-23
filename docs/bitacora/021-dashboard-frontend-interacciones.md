# Interacciones del dashboard frontend

> Fase 6: ajustes del frontend. Aplicado el 23 de noviembre de 2026 en la rama `dev`.

## Problema observado

- Los controles de siguiente/anterior de programas se basaban en la paginación del servidor mientras los filtros y la presentación dependían de otro conjunto de programas.
- El selector de programa se llenaba desde el catálogo completo aunque el resumen ya estuviera filtrado por año.
- La comparación de programas ocupaba una columna lateral, dejando los nombres y tarjetas demasiado comprimidos.
- Cada cambio del buscador de estudiantes llamaba `loadCurrentView()`, que ocultaba todo el contenido y presentaba la pantalla de carga aunque solo cambiara el texto de búsqueda.
- La ruta que restauraba directamente el nivel estudiante se llamaba a sí misma recursivamente en vez de cargar los datos.

## Cambios realizados

### Tarjetas y paginación global

Archivos: `front/partials/dashboard/screen.php`, `front/partials/dashboard/dashboard.js`, `front/partials/dashboard/data.php` y `front/partials/dashboard/style.css`.

- Se retiró el gráfico comparativo lateral y se usó el espacio para tarjetas de programa más anchas y con el nombre completo.
- La API entrega hasta 50 programas filtrados en una sola consulta; la interfaz los presenta de seis en seis.
- Para los 17 programas actuales hay tres páginas; con los 12 disponibles al filtrar el año 2024 hay dos.
- Anterior/siguiente actualizan la cuadrícula localmente y quedan deshabilitados en los límites. Los cambios de filtros vuelven a la primera página.
- La lista completa de resultados filtrados alimenta también el selector de programa, de modo que no muestra programas que no pertenecen al año/simulacro seleccionado.
- El detalle del programa conserva sus propios gráficos, indicadores y tabla de estudiantes.

### Búsqueda de estudiantes

Archivos: `front/partials/dashboard/dashboard.js` y `front/partials/dashboard/screen.php`.

- La búsqueda se mantiene con debounce de 300 ms y usa el endpoint del programa.
- La respuesta reemplaza las filas y la paginación de la tabla; no se ocultan el encabezado, los indicadores ni el gráfico, y el código no reinicia el scroll. El navegador puede ajustar el desplazamiento si la menor altura de la tabla reduce el alto total de la página.
- Un contador de solicitud descarta respuestas antiguas cuando se escribe rápidamente o se navega antes de que termine la solicitud.
- Se expone el estado de búsqueda mediante `aria-live` y se informa el error en el mismo control.

### Navegación a estudiante

`requestCurrentData()` ahora consulta el historial con `fetchStudent()` al restaurar la vista individual. Antes, esa rama invocaba recursivamente `requestCurrentData()` y nunca llegaba a una solicitud de datos.

## Por qué

El resumen debe permitir localizar los 17 programas con nombres legibles y sin que una gráfica secundaria reduzca su espacio. Mantener seis tarjetas por página deja dos filas en pantalla de escritorio y hace explícitos los límites de navegación. Reutilizar la lista del resultado filtrado mantiene sincronizados los KPI, las tarjetas y el selector. Por último, una búsqueda incremental debe conservar el contexto de lectura; recargar visualmente todo el detalle interrumpe al instructor y fuerza desplazamientos innecesarios.

## Validación

La actualización no modifica el backend ni sus contratos. La sintaxis de las plantillas quedó verificada:

```powershell
php -l front\index.php
php -l front\partials\dashboard\screen.php
php -l front\partials\dashboard\data.php
git diff --check
```

La validación del comportamiento se hizo en un navegador con respuestas de API simuladas:

- 17 programas: 6, 6 y 5 tarjetas en las tres páginas; en la última el botón siguiente queda desactivado.
- Año 2024: 12 tarjetas, dos páginas y 12 opciones de programa más «Todos».
- Búsqueda por nombre: la tabla quedó en una fila, el contenido general siguió visible, el indicador de carga global permaneció oculto y el campo conservó el foco.
- El navegador ajustó unos píxeles de scroll al reducirse la altura de la tabla; el código no reinició la página al inicio.

El navegador ejecutó el JavaScript actualizado. Node.js no está instalado en el entorno de validación; no se añadió como dependencia porque el frontend no lo necesita.
