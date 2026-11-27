// Una mitad del comparativo (ESE o CORHUILA). Plantilla: shared/compare-side.php.

import { drawBars } from './charts/bars.js';
import { addCell, setText } from './dom.js';
import { formatNumber, numberOrNull } from './format.js';

const SIN_PROGRAMA_ID = 'sin-programa';

function levelText(value) {
    const level = numberOrNull(value);
    return level === null ? 'Sin datos' : 'N' + formatNumber(level);
}

function competencyEntries(metrics) {
    const competencies = metrics && metrics.competencies ? metrics.competencies : {};
    return Object.keys(competencies).map((key) => ({
        label: competencies[key].label || key,
        value: numberOrNull(competencies[key].average)
    }));
}

/** Sin archivo de esta prueba en el periodo: "a la espera" y, si se puede, botón para subirlo. */
function renderWaiting(element, options) {
    element.querySelector('[data-side-body]').hidden = true;
    element.querySelector('[data-side-waiting]').hidden = false;
    setText(element, '[data-side-file]', options.period ? 'Periodo ' + options.period : '');

    const upload = element.querySelector('[data-side-upload]');
    const canUpload = options.period && options.uploadPeriods.includes(options.period);
    setText(element, '[data-side-waiting-text]', canUpload
        ? 'Aún no se ha subido el archivo de ' + options.label + ' de ' + options.period + '.'
        : 'No se cargó archivo de ' + options.label + ' en ' + (options.period || 'este periodo') + '.');
    upload.hidden = !canUpload;
    if (canUpload) {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'report');
        url.searchParams.set('source', options.source);
        url.searchParams.set('period', options.period);
        upload.href = url.toString();
    }
}

/** Con `onOpen`, el nombre de cada programa es un botón que abre su detalle. */
function renderPrograms(element, programs, onOpen) {
    const tbody = element.querySelector('[data-side-programs]');
    tbody.replaceChildren();
    programs.forEach((program) => {
        const row = document.createElement('tr');
        if (program.program_id === SIN_PROGRAMA_ID) {
            row.className = 'is-sin-programa';
        }
        if (onOpen) {
            const cell = document.createElement('td');
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'text-button compare-program-open';
            button.textContent = program.name + ' →';
            button.title = 'Ver estudiantes y gráfica de ' + program.name;
            button.addEventListener('click', () => onOpen(program));
            cell.appendChild(button);
            row.appendChild(cell);
        } else {
            addCell(row, program.name);
        }
        addCell(row, formatNumber(program.metrics.average_general));
        addCell(row, levelText(program.metrics.average_level));
        addCell(row, formatNumber(program.metrics.unique_students));
        tbody.appendChild(row);
    });
    element.querySelector('[data-side-programs-empty]').hidden = programs.length > 0;
}

/**
 * @param {HTMLElement} element  La sección [data-side].
 * @param {object|null} side     `ese` o `corhuila` de /compare; null = a la espera.
 * @param {{label: string, source: string, period: string|null, uploadPeriods: string[], onOpenProgram?: Function}} options
 */
export function renderSide(element, side, options) {
    if (!side) {
        renderWaiting(element, options);
        return;
    }
    element.querySelector('[data-side-waiting]').hidden = true;
    element.querySelector('[data-side-body]').hidden = false;
    setText(element, '[data-side-file]', 'Periodo ' + (side.period || options.period || '') + ' · ' + side.filename);

    const kpis = side.kpis;
    setText(element, '[data-side-average]', formatNumber(kpis.average_general));
    setText(element, '[data-side-level]', levelText(kpis.average_level));
    setText(element, '[data-side-students]', formatNumber(kpis.unique_students));
    setText(element, '[data-side-presentations]', formatNumber(kpis.presentations));

    const weakest = side.weakest_competency;
    setText(element, '[data-side-weakest]', weakest ? 'Más baja: ' + weakest.label : '');
    drawBars(
        element.querySelector('[data-side-chart]'),
        competencyEntries(kpis),
        'Competencias de ' + options.label,
        'Promedio de las 4 competencias comunes en ' + options.label + '.',
        element.querySelector('[data-side-chart-empty]')
    );
    renderPrograms(element, side.programs || [], options.onOpenProgram);
}
