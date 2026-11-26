// Conecta los controles de la pantalla con el controlador.

import { readUrlState } from './state.js';

export function bindEvents(ctx, controller) {
    const { root, state, elements } = ctx;
    const on = (selector, handler) => root.querySelector(selector).addEventListener('click', handler);

    elements.yearFilter.addEventListener('change', controller.changeYear);
    elements.periodFilter.addEventListener('change', controller.changePeriod);
    elements.momentFilter.addEventListener('change', controller.changeMoment);
    elements.subjectFilter.addEventListener('change', controller.changeSubject);
    elements.programFilter.addEventListener('change', controller.changeSelectedProgram);

    on('[data-reset-filters]', controller.resetFilters);
    on('[data-retry-dashboard]', controller.loadCurrentView);
    on('[data-program-prev]', () => controller.changeGlobalPage(-1));
    on('[data-program-next]', () => controller.changeGlobalPage(1));
    on('[data-student-prev]', () => controller.changeStudentPage(-1));
    on('[data-student-next]', () => controller.changeStudentPage(1));

    elements.studentSearch.addEventListener('input', () => {
        controller.searchStudents(elements.studentSearch.value.trim());
    });

    // Atrás / adelante del navegador.
    window.addEventListener('popstate', () => {
        readUrlState(state);
        controller.loadCurrentView();
    });
}
