// Filtros de año, simulacro, asignatura y programa, y su resumen en texto.

import { populateSelect } from './dom.js';
import { competencyEntries } from './metrics.js';

export function configureFilters(ctx, overview) {
    const { state, elements } = ctx;
    state.filters = overview.filters || state.filters;
    const years = (state.filters && state.filters.years ? state.filters.years : [])
        .map((year) => ({ value: year, label: String(year) }));
    const simulations = (state.filters && state.filters.simulations ? state.filters.simulations : [])
        .map((simulation) => ({ value: simulation, label: simulation }));

    if (!populateSelect(elements.yearFilter, years, state.year, 'Todos')) {
        state.year = '';
    }
    if (!populateSelect(elements.simulationFilter, simulations, state.simulation, 'Todos')) {
        state.simulation = '';
    }

    const metrics = overview.kpis || overview.metrics;
    const competencies = competencyEntries(metrics);
    if (competencies.length) {
        state.competencyOptions = competencies;
    }
    const subjectOptions = [
        { value: 'global', label: 'Global' },
        { value: 'all', label: 'Todas las asignaturas' }
    ].concat(state.competencyOptions.map((item) => ({ value: item.key, label: item.label })));
    if (!populateSelect(elements.subjectFilter, subjectOptions, state.subject, null)) {
        state.subject = 'global';
        elements.subjectFilter.value = 'global';
    }

    if (Array.isArray(overview.programs)) {
        const programs = overview.programs;
        populateSelect(
            elements.programFilter,
            programs.map((item) => ({ value: item.program_id, label: item.name })),
            state.selectedProgramId,
            'Todos los programas'
        );
        if (!programs.some((item) => String(item.program_id) === state.selectedProgramId)) {
            state.selectedProgramId = '';
            elements.programFilter.value = '';
        }
    }
    updateFilterContext(ctx);
}

export function updateFilterContext(ctx) {
    const { root, state } = ctx;
    const context = root.querySelector('[data-filter-context]');
    const values = [];
    if (state.year) {
        values.push('Año: ' + state.year);
    }
    if (state.simulation) {
        values.push('Simulacro: ' + state.simulation);
    }
    if (state.subject === 'all') {
        values.push('Asignatura: Todas');
    } else if (state.subject !== 'global') {
        const subject = state.competencyOptions.find((item) => item.key === state.subject);
        if (subject) {
            values.push('Asignatura: ' + subject.label);
        }
    } else {
        values.push('Asignatura: Global');
    }
    context.textContent = values.join(' · ');
}
