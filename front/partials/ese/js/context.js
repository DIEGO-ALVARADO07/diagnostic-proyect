// Contexto compartido: raíz, estado, elementos fijos y acciones de navegación.
//
// Las vistas llaman `ctx.actions.*` (abrir programa, abrir estudiante,
// cargar el programa seleccionado) sin importar el controlador; así no hay
// dependencias circulares entre módulos.

import { createState } from './state.js';

export function createContext(root) {
    return {
        root: root,
        state: createState(root),
        elements: {
            content: root.querySelector('[data-dashboard-content]'),
            loading: root.querySelector('[data-dashboard-loading]'),
            errorBox: root.querySelector('[data-dashboard-error]'),
            noImport: root.querySelector('[data-dashboard-no-import]'),
            yearFilter: root.querySelector('[data-filter-year]'),
            subjectFilter: root.querySelector('[data-filter-subject]'),
            periodFilter: root.querySelector('[data-filter-period]'),
            momentFilter: root.querySelector('[data-filter-moment]'),
            programFilter: root.querySelector('[data-program-filter]'),
            studentSearch: root.querySelector('[data-student-search]')
        },
        // Las asigna el controlador.
        actions: {
            openProgram: null,
            openStudent: null,
            loadSelectedProgram: null
        }
    };
}
