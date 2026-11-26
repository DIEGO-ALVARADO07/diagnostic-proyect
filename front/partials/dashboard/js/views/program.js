// Vista de programa: KPIs, barras por asignatura y tabla de estudiantes.

import { drawBars } from '../charts/bars.js';
import { addCell, setText } from '../dom.js';
import { configureFilters } from '../filters.js';
import { formatNumber } from '../format.js';
import { generalAverage, programCompetencyEntries } from '../metrics.js';
import { dashboardUrlForGlobal } from '../state.js';

function presentedLabel(presented) {
    if (presented === true) {
        return 'Presentó';
    }
    return presented === false ? 'No presentó' : 'Sin dato';
}

export function renderProgramStudents(ctx, program) {
    const { root } = ctx;
    const tbody = root.querySelector('[data-program-students]');
    const empty = root.querySelector('[data-empty-students]');
    tbody.replaceChildren();
    const students = program.students || [];
    students.forEach((student) => {
        const row = document.createElement('tr');
        addCell(row, student.name || 'Nombre no disponible', 'student-name-cell');
        addCell(row, student.document || 'Sin documento');
        addCell(row, student.year);
        addCell(row, student.simulation || 'Sin dato');
        addCell(row, formatNumber(student.global_score));
        addCell(row, presentedLabel(student.presented));
        const actionCell = document.createElement('td');
        if (student.document) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'text-button student-open-button';
            button.textContent = 'Ver detalle →';
            button.addEventListener('click', () => {
                ctx.actions.openStudent(student.document);
            });
            actionCell.appendChild(button);
        } else {
            actionCell.textContent = 'Sin documento';
        }
        row.appendChild(actionCell);
        tbody.appendChild(row);
    });
    empty.hidden = students.length > 0;
    setText(root, '[data-student-pages]', 'Página ' + program.page + ' de ' + program.total_pages + ' · ' + program.total_records + ' registros');
    root.querySelector('[data-student-prev]').disabled = program.page <= 1;
    root.querySelector('[data-student-next]').disabled = program.page >= program.total_pages;
    root.querySelector('.student-pagination').hidden = program.total_records === 0;
}

export function renderProgram(ctx, program) {
    const { root, state } = ctx;
    state.program = program;
    state.filters = program.filters || state.filters;
    configureFilters(ctx, { filters: program.filters, metrics: program.metrics });
    setText(root, '[data-program-title]', program.program.name);
    setText(root, '[data-program-average]', formatNumber(generalAverage(program.metrics)));
    setText(root, '[data-program-students-count]', formatNumber(program.metrics.unique_students));
    setText(root, '[data-program-presentations]', formatNumber(program.metrics.presentations));

    drawBars(
        root.querySelector('[data-program-competencies]'),
        programCompetencyEntries(state, program.metrics),
        'Desempeño de ' + program.program.name,
        'Resultados por asignatura calculados por la API.',
        root.querySelector('[data-empty-program-competencies]')
    );
    renderProgramStudents(ctx, program);
    setText(root, '[data-student-search-status]', state.studentSearch ? 'Búsqueda activa' : '');
    root.querySelector('[data-back-global]').href = dashboardUrlForGlobal(state);
}
