// Vista global: KPIs, tarjetas de programas paginadas y programa seleccionado.

import { drawBars } from '../charts/bars.js';
import { drawBubbles } from '../charts/bubbles.js';
import { setText } from '../dom.js';
import { configureFilters } from '../filters.js';
import { formatNumber } from '../format.js';
import { generalAverage, programCompetencyEntries, selectedMetric, selectedMetricLabel } from '../metrics.js';
import { PROGRAMS_PER_PAGE, dashboardUrlForProgram, updateUrl } from '../state.js';

export function renderSelectedProgram(ctx, program) {
    const { root, state } = ctx;
    const panel = root.querySelector('[data-selected-program-panel]');
    state.programFilterData = program;
    if (!program) {
        panel.hidden = true;
        return;
    }
    panel.hidden = false;
    setText(root, '[data-selected-program-name]', program.program.name);
    setText(root, '[data-selected-program-average]', formatNumber(generalAverage(program.metrics)));
    root.querySelector('[data-open-selected-program]').href = dashboardUrlForProgram(state, program.program.program_id);
    drawBars(
        root.querySelector('[data-selected-program-chart]'),
        programCompetencyEntries(state, program.metrics),
        'Resultados de ' + program.program.name,
        'Promedios de las asignaturas que devuelve la API.',
        null
    );
}

export function renderOverview(ctx, overview, loadSelected) {
    const { root, state, elements } = ctx;
    state.overview = overview;
    state.filters = overview.filters || state.filters;
    configureFilters(ctx, overview);
    setText(root, '[data-kpi-average]', formatNumber(generalAverage(overview.kpis)));
    setText(root, '[data-kpi-programs]', formatNumber(overview.kpis.programs));
    setText(root, '[data-kpi-students]', formatNumber(overview.kpis.unique_students));
    setText(root, '[data-kpi-presentations]', formatNumber(overview.kpis.presentations));

    const programs = overview.programs || [];
    const totalPages = Math.max(1, Math.ceil(programs.length / PROGRAMS_PER_PAGE));
    if (state.page > totalPages) {
        state.page = totalPages;
        updateUrl(state, true);
    }
    const start = (state.page - 1) * PROGRAMS_PER_PAGE;
    drawBubbles(
        root.querySelector('[data-program-bubbles]'),
        root.querySelector('[data-empty-bubbles]'),
        programs.slice(start, start + PROGRAMS_PER_PAGE),
        {
            label: selectedMetricLabel(state),
            valueOf: (program) => selectedMetric(state, program.metrics),
            onOpen: (program) => ctx.actions.openProgram(program.program_id)
        }
    );

    const totalPrograms = overview.total_programs;
    setText(root, '[data-program-page-label]', totalPrograms + ' programas');
    setText(root, '[data-program-pages]', 'Página ' + state.page + ' de ' + totalPages + ' · ' + totalPrograms + ' programas');
    root.querySelector('[data-program-prev]').disabled = state.page <= 1;
    root.querySelector('[data-program-next]').disabled = state.page >= totalPages;
    root.querySelector('[data-program-pagination]').hidden = totalPages <= 1;

    if (elements.programFilter.value !== state.selectedProgramId) {
        elements.programFilter.value = state.selectedProgramId;
    }
    if (state.selectedProgramId && loadSelected) {
        ctx.actions.loadSelectedProgram();
    } else if (state.selectedProgramId && state.programFilterData) {
        renderSelectedProgram(ctx, state.programFilterData);
    } else if (!state.selectedProgramId) {
        state.selectedProgramRequest += 1;
        renderSelectedProgram(ctx, null);
    }
}
