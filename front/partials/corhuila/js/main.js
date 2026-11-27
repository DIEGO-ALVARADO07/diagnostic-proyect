// Módulo CORHUILA: resultados del periodo con filtros, detalle por programa,
// tabla de estudiantes y asignación manual de programa (fases 12b y 15).
//
// El periodo solo ofrece los que tienen archivo de CORHUILA (corhuila_periods);
// al entrar se usa el más reciente. Programa, semestre y búsqueda van a
// /excel/dashboard/{import_id}/results: con un programa elegido, la página
// pasa a su detalle (KPIs, gráfica y estudiantes de ese programa). Todo queda
// en la URL, así que atrás / adelante del navegador funcionan.

import { apiPost, apiRequest, errorMessage } from '../../shared/js/api.js';
import { renderSide } from '../../shared/js/compare-side.js';
import { populateSelect, setText, showState } from '../../shared/js/dom.js';
import { formatNumber } from '../../shared/js/format.js';
import { renderResults } from './results.js';
import { renderWithoutProgram } from './without-program.js';

const root = document.querySelector('[data-corhuila]');
const SIN_PROGRAMA_ID = 'sin-programa';

if (root) {
    const elements = {
        loading: root.querySelector('[data-corhuila-loading]'),
        errorBox: root.querySelector('[data-corhuila-error]'),
        noImport: root.querySelector('[data-corhuila-empty]'),
        content: root.querySelector('[data-corhuila-content]'),
        period: root.querySelector('[data-corhuila-period]'),
        program: root.querySelector('[data-corhuila-program]'),
        semester: root.querySelector('[data-corhuila-semester]'),
        search: root.querySelector('[data-corhuila-search]'),
        side: root.querySelector('[data-side="corhuila"]'),
        programHeading: root.querySelector('[data-program-heading]'),
        resultsStatus: root.querySelector('[data-results-status]'),
        withoutPanel: root.querySelector('[data-without-panel]'),
        status: root.querySelector('[data-without-status]'),
        resolve: root.querySelector('[data-resolve]')
    };
    const positiveInt = (value) => {
        const number = parseInt(value, 10);
        return Number.isInteger(number) && number > 0 ? number : 1;
    };
    const state = {
        period: root.dataset.period || '',
        programId: root.dataset.programId || '',
        semester: root.dataset.semester || '',
        search: root.dataset.search || '',
        page: positiveInt(root.dataset.page),
        csrfToken: root.dataset.csrfToken,
        uploadPeriods: JSON.parse(root.dataset.uploadPeriods || '[]'),
        catalog: null,
        side: null,
        results: null,
        requestNumber: 0,
        resultsRequest: 0,
        searchTimer: null
    };
    elements.search.value = state.search;

    const setStatus = (message, isError) => {
        elements.status.textContent = message;
        elements.status.classList.toggle('is-error', Boolean(isError));
    };

    const pageUrl = () => {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'corhuila');
        const values = {
            period: state.period,
            program_id: state.programId,
            semester: state.semester,
            search: state.search,
            page: state.page > 1 ? String(state.page) : ''
        };
        Object.keys(values).forEach((key) => {
            if (values[key]) {
                url.searchParams.set(key, values[key]);
            }
        });
        return url;
    };
    /** `push` = nueva entrada en el historial (entrar o salir de un programa). */
    const updateUrl = (push) => {
        if (push) {
            window.history.pushState({}, '', pageUrl());
        } else {
            window.history.replaceState({}, '', pageUrl());
        }
    };

    const readUrl = () => {
        const params = new URLSearchParams(window.location.search);
        state.period = params.get('period') || '';
        state.programId = params.get('program_id') || '';
        state.semester = params.get('semester') || '';
        state.search = params.get('search') || '';
        state.page = positiveInt(params.get('page'));
        elements.search.value = state.search;
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

    const fetchResults = () => apiRequest({
        resource: 'results',
        import_id: state.side.import_id,
        program_id: state.programId,
        semester: state.semester,
        search: state.search,
        page: state.page
    });

    /** El elegido siempre queda en la lista, aunque la búsqueda lo deje en 0. */
    const withSelected = (options, selected, fallbackLabel) => {
        if (selected && !options.some((option) => option.value === selected)) {
            return options.concat([{ value: selected, label: fallbackLabel, count: 0 }]);
        }
        return options;
    };

    const renderFilters = (results) => {
        const programs = withSelected(results.program_options || [], state.programId,
            results.program ? results.program.name : state.programId);
        populateSelect(elements.program, programs.map((option) => ({
            value: option.value, label: option.label + ' (' + formatNumber(option.count) + ')'
        })), state.programId, 'Todos los programas');
        const semesters = withSelected(results.semester_options || [], state.semester, state.semester);
        populateSelect(elements.semester, semesters.map((option) => ({
            value: option.value, label: option.label + ' (' + formatNumber(option.count) + ')'
        })), state.semester, 'Todos los semestres');

        const parts = ['Periodo: ' + state.period];
        parts.push(results.program ? 'Programa: ' + results.program.name : 'Todos los programas');
        const semester = semesters.find((option) => option.value === state.semester);
        parts.push(semester ? semester.label : 'Todos los semestres');
        if (state.search) {
            parts.push('Búsqueda: “' + state.search + '”');
        }
        setText(root, '[data-corhuila-context]', parts.join(' · '));
    };

    /** La competencia más baja de las métricas (como en el dashboard). */
    const weakest = (metrics) => {
        const competencies = (metrics && metrics.competencies) || {};
        return Object.keys(competencies).reduce((lowest, key) => {
            const average = competencies[key].average;
            if (average === null || average === undefined || (lowest && lowest.average <= average)) {
                return lowest;
            }
            return { key: key, label: competencies[key].label || key, average: average };
        }, null);
    };

    const renderSummary = (results) => {
        const inProgram = Boolean(results.program);
        elements.programHeading.hidden = !inProgram;
        setText(root, '[data-program-title]', inProgram ? results.program.name : '');
        renderSide(elements.side, {
            period: state.period,
            filename: state.side.filename,
            kpis: results.metrics,
            programs: inProgram ? [] : results.programs,
            weakest_competency: weakest(results.metrics)
        }, {
            label: inProgram ? results.program.name : 'CORHUILA',
            source: 'CORHUILA',
            period: state.period,
            uploadPeriods: state.uploadPeriods,
            onOpenProgram: (program) => openProgram(program.program_id)
        });
        setText(elements.side, '[data-side-title]', inProgram ? results.program.name : 'CORHUILA');
        elements.side.querySelector('[data-side-programs-block]').hidden = inProgram;
        setText(elements.side, '[data-side-programs-hint]',
            'Del mejor al más bajo; "Sin programa" va al final. Haz clic en un programa para ver sus estudiantes y su gráfica.');
        // "Sin programa" por revisar: en la vista general o en ese mismo programa.
        elements.withoutPanel.hidden = inProgram && state.programId !== SIN_PROGRAMA_ID;
    };

    const renderStudents = (results) => {
        renderResults(root.querySelector('[data-results-rows]'), results.students || []);
        setText(root, '[data-results-total]', formatNumber(results.total_records) + ' filas');
        setText(root, '[data-results-copy]', results.program
            ? 'Estudiantes de ' + results.program.name + ' en ' + state.period + '.'
            : 'Todos los estudiantes del periodo. Quien está en dos programas aparece una vez por programa.');
        root.querySelector('[data-results-empty]').hidden = (results.students || []).length > 0;
        setText(root, '[data-results-page]', 'Página ' + results.page + ' de ' + results.total_pages +
            ' · ' + formatNumber(results.total_records) + ' filas');
        root.querySelector('[data-results-prev]').disabled = results.page <= 1;
        root.querySelector('[data-results-next]').disabled = results.page >= results.total_pages;
        root.querySelector('[data-results-pagination]').hidden = results.total_pages <= 1;
    };

    const render = (results) => {
        state.results = results;
        renderFilters(results);
        renderSummary(results);
        renderStudents(results);
    };

    /** Un programa que no está en la carga de este periodo vuelve a "Todos". */
    const resultsOrReset = () => fetchResults().catch((error) => {
        if (error.status === 404 && state.programId) {
            state.programId = '';
            state.page = 1;
            return fetchResults();
        }
        throw error;
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
        state.resultsRequest += 1;
        window.clearTimeout(state.searchTimer);
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
            state.side = response.corhuila;
            populateSelect(elements.period, periods.map((period) => ({ value: period, label: period })), state.period, null);
            if (!state.side) {
                renderSide(elements.side, null, {
                    label: 'CORHUILA', source: 'CORHUILA', period: state.period, uploadPeriods: state.uploadPeriods
                });
                showState(elements, 'content');
                return null;
            }
            return Promise.all([resultsOrReset(), loadWithoutProgram()]).then(([results]) => {
                if (requestNumber !== state.requestNumber) {
                    return;
                }
                render(results);
                updateUrl(false);
                showState(elements, 'content');
            });
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-corhuila-error-message]', errorMessage(error));
            showState(elements, 'error');
        });
    };

    /** Cambio de programa, semestre, búsqueda o página: solo vuelve a pedir los resultados. */
    const reloadResults = (push) => {
        if (!state.side) {
            return;
        }
        const requestId = ++state.resultsRequest;
        elements.resultsStatus.textContent = state.search ? 'Buscando…' : 'Cargando resultados…';
        elements.resultsStatus.classList.remove('is-error');
        updateUrl(push);
        resultsOrReset().then((results) => {
            if (requestId !== state.resultsRequest) {
                return;
            }
            render(results);
            elements.resultsStatus.textContent = '';
            updateUrl(false);
        }).catch((error) => {
            if (requestId !== state.resultsRequest) {
                return;
            }
            elements.resultsStatus.textContent = errorMessage(error);
            elements.resultsStatus.classList.add('is-error');
        });
    };

    function openProgram(programId) {
        state.programId = String(programId || '');
        state.page = 1;
        reloadResults(true);
        root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

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
        // Otro periodo es otra carga: el programa se conserva si existe allí.
        state.period = elements.period.value;
        state.semester = '';
        state.page = 1;
        setStatus('');
        load();
    });
    elements.program.addEventListener('change', () => openProgram(elements.program.value));
    elements.semester.addEventListener('change', () => {
        state.semester = elements.semester.value;
        state.page = 1;
        reloadResults(false);
    });
    elements.search.addEventListener('input', () => {
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => {
            state.search = elements.search.value.trim();
            state.page = 1;
            reloadResults(false);
        }, 300);
    });
    root.querySelector('[data-back-all]').addEventListener('click', () => openProgram(''));
    root.querySelector('[data-corhuila-reset]').addEventListener('click', () => {
        state.programId = '';
        state.semester = '';
        state.search = '';
        state.page = 1;
        elements.search.value = '';
        reloadResults(false);
    });
    root.querySelector('[data-results-prev]').addEventListener('click', () => {
        if (state.page > 1) {
            state.page -= 1;
            reloadResults(false);
        }
    });
    root.querySelector('[data-results-next]').addEventListener('click', () => {
        if (state.results && state.page < state.results.total_pages) {
            state.page += 1;
            reloadResults(false);
        }
    });

    elements.resolve.addEventListener('click', () => {
        elements.resolve.disabled = true;
        setStatus('Recalculando el cruce con matriculados y el histórico de ESE…');
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

    // Atrás / adelante del navegador (entrar y salir de un programa).
    window.addEventListener('popstate', () => {
        const previousPeriod = state.period;
        readUrl();
        if (state.period && state.period === previousPeriod && state.side) {
            reloadResults(false);
        } else {
            load();
        }
    });

    load();
}
