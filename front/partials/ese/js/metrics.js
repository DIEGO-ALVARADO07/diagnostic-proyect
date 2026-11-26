// Lectura de las métricas que devuelve la API según la asignatura elegida.

import { numberOrNull } from '../../shared/js/format.js';

function isGeneralSubject(state) {
    return state.subject === 'global' || state.subject === 'all';
}

export function generalAverage(metrics) {
    if (!metrics) {
        return null;
    }
    let average = metrics.average_general;
    if (average === undefined) {
        average = metrics.average_global;
    }
    return numberOrNull(average);
}

export function competencyEntries(metrics) {
    const competencies = metrics && metrics.competencies ? metrics.competencies : {};
    return Object.keys(competencies).map((key) => ({
        key: key,
        label: competencies[key].label || key,
        value: numberOrNull(competencies[key].average)
    }));
}

export function selectedMetric(state, metrics) {
    if (!metrics) {
        return null;
    }
    if (isGeneralSubject(state)) {
        return generalAverage(metrics);
    }
    const competency = metrics.competencies && metrics.competencies[state.subject];
    return competency ? numberOrNull(competency.average) : null;
}

export function selectedMetricLabel(state) {
    if (isGeneralSubject(state)) {
        return 'Promedio general';
    }
    const selected = state.competencyOptions.find((item) => item.key === state.subject);
    return selected ? selected.label : 'Promedio general';
}

export function programCompetencyEntries(state, metrics) {
    const competencies = competencyEntries(metrics);
    if (isGeneralSubject(state)) {
        return competencies;
    }
    return competencies.filter((item) => item.key === state.subject);
}
