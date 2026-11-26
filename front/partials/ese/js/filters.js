// Filtros de año, periodo, momento, asignatura y programa, y su resumen en texto.
//
// Como en el dashboard: Año → Periodo del año → Momento, en cascada. No hay
// "Todos los años"; al entrar se ve el periodo más reciente y, para el
// histórico, se elige otro año o "Todo el año".

import { populateSelect } from '../../shared/js/dom.js';
import { competencyEntries } from './metrics.js';

/** Año más reciente de la carga de ESE, como texto ('' si no hay años). */
export function latestYear(filters) {
    const years = filters && Array.isArray(filters.years) ? filters.years : [];
    return years.length ? String(Math.max.apply(null, years)) : '';
}

/** Periodos (AAAA-S) del año con datos, el más reciente primero. */
function periodsOfYear(filters, year) {
    const periods = filters && Array.isArray(filters.periods) ? filters.periods : [];
    return periods.filter((period) => period.startsWith(year + '-')).sort().reverse();
}

/** Periodo más reciente del año ('' si el año no tiene periodos). */
export function latestPeriodOf(filters, year) {
    return periodsOfYear(filters, year)[0] || '';
}

/** Momentos del periodo; con "Todo el año", los de todos sus periodos. */
function momentsFor(filters, year, period) {
    const byPeriod = (filters && filters.moments_by_period) || {};
    const periods = period ? [period] : periodsOfYear(filters, year);
    const moments = new Set();
    periods.forEach((item) => (byPeriod[item] || []).forEach((moment) => moments.add(moment)));
    return Array.from(moments).sort((a, b) => a - b);
}

/** Llena Periodo y Momento según el año; lo que no aplica vuelve a "Todo el año" / "Todos". */
export function refreshPeriodOptions(ctx) {
    const { state, elements } = ctx;
    const periods = periodsOfYear(state.filters, state.year).map((period) => ({
        value: period,
        label: 'Periodo ' + period.slice(-1) + ' (' + period + ')'
    }));
    if (!populateSelect(elements.periodFilter, periods, state.period, 'Todo el año')) {
        state.period = '';
    }
    const moments = momentsFor(state.filters, state.year, state.period)
        .map((moment) => ({ value: moment, label: 'Momento ' + moment }));
    if (!populateSelect(elements.momentFilter, moments, state.moment, 'Todos')) {
        state.moment = '';
    }
}

export function configureFilters(ctx, overview) {
    const { state, elements } = ctx;
    state.filters = overview.filters || state.filters;
    const years = (state.filters && state.filters.years ? state.filters.years : [])
        .slice()
        .sort((a, b) => b - a)
        .map((year) => ({ value: year, label: String(year) }));

    // Sin opción "Todos": si el año no aplica, queda el más reciente.
    if (!populateSelect(elements.yearFilter, years, state.year, null)) {
        state.year = elements.yearFilter.value;
    }
    refreshPeriodOptions(ctx);

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
    values.push(state.period ? 'Periodo: ' + state.period : 'Periodo: todo el año');
    if (state.moment) {
        values.push('Momento ' + state.moment);
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
