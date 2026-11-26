// Arranque del dashboard. Se carga desde index.php con type="module".
//
// Mapa de módulos:
//   api.js        peticiones al proxy data.php y mensajes de error
//   state.js      estado y URL (filtros, nivel, página)
//   context.js    raíz, estado, elementos y acciones compartidas
//   format.js     números y textos
//   metrics.js    lectura de métricas según la asignatura elegida
//   dom.js        ayudas de pantalla (textos, selects, celdas)
//   filters.js    selects de filtros y su resumen
//   charts/*      gráficas SVG y tarjetas de programa
//   views/*       vistas global, programa y estudiante
//   controller.js carga de datos y navegación
//   events.js     eventos de los controles

import { createContext } from './context.js';
import { createController } from './controller.js';
import { bindEvents } from './events.js';
import { readUrlState } from './state.js';

const root = document.querySelector('[data-dashboard]');

if (root) {
    const ctx = createContext(root);
    const controller = createController(ctx);
    bindEvents(ctx, controller);

    readUrlState(ctx.state);
    ctx.elements.studentSearch.value = ctx.state.studentSearch;
    controller.loadCurrentView();
}
