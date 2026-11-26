// Módulo CORHUILA: resultados del periodo y asignación manual de programa (fase 12b).
//
// El periodo solo ofrece los que tienen archivo de CORHUILA (corhuila_periods);
// al entrar se usa el más reciente.

import { apiPost, apiRequest, errorMessage } from '../../shared/js/api.js';
import { renderSide } from '../../shared/js/compare-side.js';
import { populateSelect, setText, showState } from '../../shared/js/dom.js';
import { formatNumber } from '../../shared/js/format.js';
import { renderWithoutProgram } from './without-program.js';

const root = document.querySelector('[data-corhuila]');

if (root) {
    const elements = {
        loading: root.querySelector('[data-corhuila-loading]'),
        errorBox: root.querySelector('[data-corhuila-error]'),
        noImport: root.querySelector('[data-corhuila-empty]'),
        content: root.querySelector('[data-corhuila-content]'),
        period: root.querySelector('[data-corhuila-period]'),
        status: root.querySelector('[data-without-status]'),
        resolve: root.querySelector('[data-resolve]')
    };
    const state = {
        period: root.dataset.period || '',
        csrfToken: root.dataset.csrfToken,
        uploadPeriods: JSON.parse(root.dataset.uploadPeriods || '[]'),
        catalog: null,
        requestNumber: 0
    };

    const setStatus = (message, isError) => {
        elements.status.textContent = message;
        elements.status.classList.toggle('is-error', Boolean(isError));
    };

    const updateUrl = () => {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'corhuila');
        if (state.period) {
            url.searchParams.set('period', state.period);
        }
        window.history.replaceState({}, '', url);
    };

    const compare = (period) => apiRequest({ resource: 'compare', period: period });
    const catalog = () => (state.catalog
        ? Promise.resolve(state.catalog)
        : apiRequest({ resource: 'catalog' }).then((result) => {
            state.catalog = result.programs || [];
            return state.catalog;
        }));

    /** Pide /compare del periodo de CORHUILA elegido (o del más reciente si no aplica). */
    const compareForCorhuila = () => compare(state.period).then((response) => {
        const periods = response.filters.corhuila_periods || [];
        if (!periods.length) {
            return { response: response, periods: periods };
        }
        if (!periods.includes(response.period)) {
            state.period = periods[0];
            return compare(state.period).then((again) => ({ response: again, periods: periods }));
        }
        return { response: response, periods: periods };
    });

    const loadWithoutProgram = () => Promise.all([
        apiRequest({ resource: 'without_program', period: state.period }),
        catalog()
    ]).then(([result, programs]) => {
        setText(root, '[data-without-total]', formatNumber(result.total));
        root.querySelector('[data-without-empty]').hidden = result.students.length > 0;
        renderWithoutProgram(root.querySelector('[data-without-rows]'), result.students, programs, saveProgram);
    });

    const load = () => {
        const requestNumber = ++state.requestNumber;
        showState(elements, 'loading');
        compareForCorhuila().then(({ response, periods }) => {
            if (requestNumber !== state.requestNumber) {
                return null;
            }
            if (!periods.length) {
                showState(elements, 'empty');
                return null;
            }
            state.period = response.period;
            populateSelect(elements.period, periods.map((period) => ({ value: period, label: period })), state.period, null);
            renderSide(root.querySelector('[data-side="corhuila"]'), response.corhuila, {
                label: 'CORHUILA', source: 'CORHUILA', period: response.period, uploadPeriods: state.uploadPeriods
            });
            updateUrl();
            return loadWithoutProgram().then(() => {
                if (requestNumber === state.requestNumber) {
                    showState(elements, 'content');
                }
            });
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-corhuila-error-message]', errorMessage(error));
            showState(elements, 'error');
        });
    };

    /** Guarda el programa y vuelve a cargar: el estudiante sale de la lista y los promedios cambian. */
    function saveProgram(student, programId) {
        setStatus('Guardando el programa de ' + student.name + '…');
        return apiPost('assign_program', { student_id: student.student_id, program_id: programId }, state.csrfToken)
            .then((result) => {
                const program = (state.catalog || []).find((item) => Number(item.program_id) === programId);
                setStatus('Se asignó ' + (program ? program.name : 'el programa') + ' a ' + student.name +
                    '. Quedan ' + formatNumber(result.without_program) + ' estudiantes sin programa en total.');
                load();
            })
            .catch((error) => {
                setStatus(errorMessage(error), true);
                throw error;
            });
    }

    elements.period.addEventListener('change', () => {
        state.period = elements.period.value;
        setStatus('');
        load();
    });

    elements.resolve.addEventListener('click', () => {
        elements.resolve.disabled = true;
        setStatus('Recalculando el cruce con el histórico de ESE…');
        apiPost('resolve', {}, state.csrfToken).then((result) => {
            setStatus('Cruce recalculado: cambiaron ' + formatNumber(result.changed_rows) +
                ' filas y quedan ' + formatNumber(result.without_program) + ' estudiantes sin programa en total.');
            load();
        }).catch((error) => {
            setStatus(errorMessage(error), true);
        }).finally(() => {
            elements.resolve.disabled = false;
        });
    });

    root.querySelector('[data-corhuila-retry]').addEventListener('click', load);

    load();
}
