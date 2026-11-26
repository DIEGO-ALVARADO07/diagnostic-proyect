// Hallazgos en común bajo las dos mitades: programa más bajo y competencia más baja.

import { setText } from '../../shared/js/dom.js';
import { formatNumber, numberOrNull } from '../../shared/js/format.js';

function part(label, value, format) {
    return numberOrNull(value) === null ? label + ': sin datos' : label + ': ' + format(value);
}

const level = (value) => 'N' + formatNumber(value);

export function renderHighlights(root, response) {
    const worst = response.worst_program;
    setText(root, '[data-worst-name]', worst ? worst.name : 'Sin datos para estos filtros');
    setText(root, '[data-worst-level]', worst ? level(worst.average_level) : '—');
    setText(root, '[data-worst-ese]', worst ? part('ESE', worst.ese_average_level, level) : '');
    setText(root, '[data-worst-corhuila]', worst ? part('CORHUILA', worst.corhuila_average_level, level) : '');

    const lowest = response.lowest_common_competency;
    setText(root, '[data-lowest-name]', lowest ? lowest.label : 'Sin datos para estos filtros');
    setText(root, '[data-lowest-average]', lowest ? formatNumber(lowest.average) : '—');
    setText(root, '[data-lowest-ese]', lowest ? part('ESE', lowest.ese_average, formatNumber) : '');
    setText(root, '[data-lowest-corhuila]', lowest ? part('CORHUILA', lowest.corhuila_average, formatNumber) : '');

    setText(root, '[data-compare-note]', response.note ? 'Nota: ' + response.note : '');
}
