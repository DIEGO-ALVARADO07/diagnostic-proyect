// Vista de estudiante: último intento, evolución y puntajes por asignatura.

import { drawBars } from '../../../shared/js/charts/bars.js';
import { drawStudentTrend } from '../../../shared/js/charts/trend.js';
import { setText } from '../../../shared/js/dom.js';
import { updateFilterContext } from '../filters.js';
import { formatNumber, numberOrNull } from '../../../shared/js/format.js';
import { generalAverage, selectedMetricLabel } from '../metrics.js';
import { dashboardUrlForProgram } from '../state.js';

function isGeneralSubject(state) {
    return state.subject === 'global' || state.subject === 'all';
}

/** Intentos del estudiante en el programa abierto, con los filtros de año y simulacro. */
function filteredHistory(state, student) {
    return (student.history || []).filter((attempt) => attempt.program_id === state.programId &&
        (!state.year || String(attempt.year) === state.year) &&
        (!state.simulation || attempt.simulation === state.simulation));
}

function renderScore(ctx, latest) {
    const { root, state } = ctx;
    let score;
    let scoreLabel;
    if (!latest) {
        score = null;
        scoreLabel = isGeneralSubject(state) ? 'Puntaje global' : selectedMetricLabel(state);
    } else if (isGeneralSubject(state)) {
        score = numberOrNull(latest.global_score);
        scoreLabel = 'Puntaje global';
    } else {
        score = latest.scores ? numberOrNull(latest.scores[state.subject]) : null;
        scoreLabel = selectedMetricLabel(state);
    }
    setText(root, '[data-student-score-label]', scoreLabel);
    setText(root, '[data-student-score]', formatNumber(score));
    setText(root, '[data-student-program-average]', isGeneralSubject(state) && latest
        ? formatNumber(generalAverage({
            average_general: latest.program_average_general,
            average_global: latest.program_average_global
        }))
        : 'No disponible');
}

function renderChart(ctx, student, history, latest) {
    const { root, state } = ctx;
    const svg = root.querySelector('[data-student-history]');
    const empty = root.querySelector('[data-empty-history]');

    if (state.subject === 'all' && latest && latest.scores) {
        const metricEntries = state.competencyOptions.map((competency) => ({
            label: competency.label,
            value: numberOrNull(latest.scores[competency.key])
        }));
        setText(root, '[data-student-chart-title]', 'Resultados por asignatura · último intento');
        drawBars(
            svg,
            metricEntries,
            'Resultados por asignatura de ' + (student.name || 'estudiante'),
            'Puntajes del último intento en las asignaturas disponibles.',
            empty
        );
        return;
    }

    const subjectKey = state.subject === 'global' ? null : state.subject;
    const subjectName = state.subject === 'global' ? 'Global' : selectedMetricLabel(state);
    setText(root, '[data-student-chart-title]', 'Evolución · ' + subjectName);
    const historyEntries = history.map((attempt) => ({
        label: String(attempt.year) + ' · ' + (attempt.simulation || 'Simulacro'),
        value: subjectKey === null
            ? numberOrNull(attempt.global_score)
            : numberOrNull(attempt.scores && attempt.scores[subjectKey])
    }));
    drawStudentTrend(svg, historyEntries, student.name || 'estudiante', empty);
}

function renderScoreCards(ctx, latest) {
    const { root, state } = ctx;
    const scoresContainer = root.querySelector('[data-student-scores]');
    scoresContainer.replaceChildren();
    if (!latest) {
        setText(root, '[data-student-attempt-context]', 'Sin intentos para estos filtros');
        const emptyMessage = document.createElement('p');
        emptyMessage.className = 'empty-detail-message';
        emptyMessage.textContent = 'No hay resultados para este estudiante en los filtros seleccionados.';
        scoresContainer.appendChild(emptyMessage);
        return;
    }

    setText(root, '[data-student-attempt-context]', String(latest.year) + ' · ' + latest.simulation);
    const entries = [{ label: 'Global', value: numberOrNull(latest.global_score) }];
    state.competencyOptions.forEach((competency) => {
        entries.push({
            label: competency.label,
            value: numberOrNull(latest.scores && latest.scores[competency.key]),
            level: latest.levels && latest.levels[competency.key]
        });
    });
    entries.forEach((entry) => {
        const card = document.createElement('div');
        card.className = 'student-score-item';
        const label = document.createElement('span');
        label.textContent = entry.label;
        const value = document.createElement('strong');
        value.textContent = formatNumber(entry.value);
        card.appendChild(label);
        card.appendChild(value);
        if (entry.level) {
            const level = document.createElement('small');
            level.textContent = /^[1-4]$/.test(entry.level) ? 'Nivel ' + entry.level : entry.level;
            card.appendChild(level);
        }
        scoresContainer.appendChild(card);
    });
}

export function renderStudent(ctx, student) {
    const { root, state } = ctx;
    state.student = student;
    const program = student.programs.find((item) => item.program_id === state.programId);
    const history = filteredHistory(state, student);
    const latest = history.length ? history[history.length - 1] : null;

    setText(root, '[data-student-title]', student.name || 'Estudiante');
    setText(root, '[data-student-document]', student.document ? 'Documento: ' + student.document : 'Documento no disponible');
    setText(root, '[data-student-program]', program ? program.name : (latest ? latest.program : 'Programa no disponible'));
    setText(root, '[data-student-attempts]', formatNumber(history.length));

    renderScore(ctx, latest);
    renderChart(ctx, student, history, latest);
    renderScoreCards(ctx, latest);

    root.querySelector('[data-back-program]').href = dashboardUrlForProgram(state, state.programId);
    updateFilterContext(ctx);
}
