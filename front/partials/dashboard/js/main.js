// Dashboard principal: ESE frente a CORHUILA en un periodo (fase 12b).
//
// Filtros en cascada: Año → Periodo del año → Momento (solo ESE) → Programa.
// Al entrar no se envía periodo y la API devuelve el último cargado; los
// selects solo ofrecen combinaciones que tienen datos.

import { apiRequest, errorMessage } from '../../shared/js/api.js';
import { populateSelect, setText, showState } from '../../shared/js/dom.js';
import { renderHighlights } from './highlights.js';
import { semestersOf, splitPeriod, yearsOf } from './periods.js';
import { renderSide } from '../../shared/js/compare-side.js';

const root = document.querySelector('[data-compare]');

if (root) {
    const elements = {
        loading: root.querySelector('[data-compare-loading]'),
        errorBox: root.querySelector('[data-compare-error]'),
        noImport: root.querySelector('[data-compare-empty]'),
        content: root.querySelector('[data-compare-content]'),
        year: root.querySelector('[data-compare-year]'),
        semester: root.querySelector('[data-compare-semester]'),
        moment: root.querySelector('[data-compare-moment]'),
        program: root.querySelector('[data-compare-program]')
    };
    const state = {
        period: root.dataset.period || '',
        moment: root.dataset.moment || '',
        programId: root.dataset.programId || '',
        uploadPeriods: JSON.parse(root.dataset.uploadPeriods || '[]'),
        response: null,
        requestNumber: 0
    };

    const updateUrl = () => {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'dashboard');
        if (state.period) {
            url.searchParams.set('period', state.period);
        }
        if (state.moment) {
            url.searchParams.set('moment', state.moment);
        }
        if (state.programId) {
            url.searchParams.set('program_id', state.programId);
        }
        window.history.replaceState({}, '', url);
    };

    const fillFilters = (response) => {
        const filters = response.filters;
        const current = splitPeriod(response.period);
        const years = yearsOf(filters.periods);
        populateSelect(elements.year, years.map((year) => ({ value: year, label: year })), current.year, null);
        populateSelect(
            elements.semester,
            semestersOf(filters.periods, current.year).map((semester) => ({
                value: semester,
                label: 'Periodo ' + semester + ' (' + current.year + '-' + semester + ')'
            })),
            current.semester,
            null
        );
        populateSelect(
            elements.moment,
            filters.moments.map((moment) => ({ value: moment, label: 'Momento ' + moment })),
            state.moment,
            'Todos'
        );
        populateSelect(
            elements.program,
            filters.programs.map((program) => ({ value: program.program_id, label: program.name })),
            state.programId,
            'Todos los programas'
        );

        const momentLabel = state.moment ? 'Momento ' + state.moment : 'Todos los momentos';
        const program = filters.programs.find((item) => item.program_id === state.programId);
        setText(root, '[data-compare-context]', [
            'Periodo: ' + response.period,
            'ESE: ' + momentLabel,
            'Programa: ' + (program ? program.name : 'Todos')
        ].join(' · '));
    };

    const render = (response) => {
        fillFilters(response);
        renderSide(root.querySelector('[data-side="ese"]'), response.ese, {
            label: 'ESE', source: 'ESE', period: response.period, uploadPeriods: state.uploadPeriods
        });
        renderSide(root.querySelector('[data-side="corhuila"]'), response.corhuila, {
            label: 'CORHUILA', source: 'CORHUILA', period: response.period, uploadPeriods: state.uploadPeriods
        });
        renderHighlights(root, response);
    };

    /** Si un filtro de la URL no aplica al periodo (momento o programa inexistente), se quita. */
    const invalidFilter = (response) => {
        const filters = response.filters;
        if (state.period && !filters.periods.includes(state.period)) {
            state.period = '';
            return true;
        }
        if (state.moment && !filters.moments.includes(Number(state.moment))) {
            state.moment = '';
            return true;
        }
        if (state.programId && !filters.programs.some((item) => item.program_id === state.programId)) {
            state.programId = '';
            return true;
        }
        return false;
    };

    const load = () => {
        const requestNumber = ++state.requestNumber;
        showState(elements, 'loading');
        apiRequest({
            resource: 'compare',
            period: state.period,
            moment: state.moment,
            program_id: state.programId
        }).then((response) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            if (!response.period) {
                showState(elements, 'empty');
                return;
            }
            if (invalidFilter(response)) {
                load();
                return;
            }
            state.response = response;
            state.period = response.period;
            showState(elements, 'content');
            render(response);
            updateUrl();
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-compare-error-message]', errorMessage(error));
            showState(elements, 'error');
        });
    };

    // Cambiar de año elige el periodo más reciente de ese año. Cambiar de
    // periodo quita el momento, porque cada periodo tiene sus propios momentos.
    elements.year.addEventListener('change', () => {
        const periods = state.response ? state.response.filters.periods : [];
        const semester = semestersOf(periods, elements.year.value)[0];
        state.period = semester ? elements.year.value + '-' + semester : '';
        state.moment = '';
        load();
    });
    elements.semester.addEventListener('change', () => {
        state.period = elements.year.value + '-' + elements.semester.value;
        state.moment = '';
        load();
    });
    elements.moment.addEventListener('change', () => {
        state.moment = elements.moment.value;
        load();
    });
    elements.program.addEventListener('change', () => {
        state.programId = elements.program.value;
        load();
    });
    root.querySelector('[data-compare-reset]').addEventListener('click', () => {
        state.period = '';
        state.moment = '';
        state.programId = '';
        load();
    });
    root.querySelector('[data-compare-retry]').addEventListener('click', load);

    load();
}
