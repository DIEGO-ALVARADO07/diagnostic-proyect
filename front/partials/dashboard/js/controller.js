// Carga de datos y navegación entre las vistas global, programa y estudiante.
//
// `requestNumber` descarta respuestas viejas: si el usuario cambia de vista o
// de filtro antes de que llegue una respuesta, esa respuesta se ignora.

import { apiRequest, errorMessage, makeError } from './api.js';
import { setText, showState } from './dom.js';
import { configureFilters, updateFilterContext } from './filters.js';
import { PROGRAMS_PER_PAGE, buildFilterParams, updateUrl } from './state.js';
import { renderOverview, renderSelectedProgram } from './views/overview.js';
import { renderProgram, renderProgramStudents } from './views/program.js';
import { renderStudent } from './views/student.js';

export function createController(ctx) {
    const { root, state, elements } = ctx;

    function showError(error) {
        setText(root, '[data-error-message]', errorMessage(error));
        showState(elements, 'error');
    }

    function renderCurrentData() {
        root.querySelectorAll('[data-level-view]').forEach((view) => {
            view.hidden = view.dataset.levelView !== state.level;
        });
        if (state.level === 'global' && state.overview) {
            renderOverview(ctx, state.overview, false);
        } else if (state.level === 'program' && state.program) {
            renderProgram(ctx, state.program);
        } else if (state.level === 'student' && state.student) {
            renderStudent(ctx, state.student);
        }
        updateFilterContext(ctx);
    }

    // --- Peticiones -------------------------------------------------------

    function isCurrent(requestNumber) {
        return requestNumber === undefined || requestNumber === state.requestNumber;
    }

    function fetchOverview(requestNumber) {
        return apiRequest(Object.assign({
            resource: 'overview',
            import_id: state.importId,
            page: 1
        }, buildFilterParams(state))).then((overview) => {
            if (isCurrent(requestNumber)) {
                state.overview = overview;
                state.importId = overview.import_id;
                state.filters = overview.filters;
            }
            return overview;
        });
    }

    function fetchProgram(requestNumber) {
        return apiRequest(Object.assign({
            resource: 'program',
            import_id: state.importId,
            program_id: state.programId,
            page: state.page,
            search: state.studentSearch
        }, buildFilterParams(state))).then((program) => {
            if (isCurrent(requestNumber)) {
                state.program = program;
                state.filters = program.filters;
            }
            return program;
        });
    }

    function fetchStudent() {
        if (!state.studentRef) {
            return Promise.reject(makeError('Selecciona de nuevo el estudiante para consultar su historial.', 404));
        }
        return apiRequest({ resource: 'student', ref: state.studentRef }).then((student) => {
            state.student = student;
            return student;
        });
    }

    function requestCurrentData(requestNumber) {
        if (state.level === 'program') {
            return fetchProgram(requestNumber);
        }
        if (state.level === 'student') {
            return fetchStudent();
        }
        return fetchOverview(requestNumber);
    }

    /** Sin import_id: pide la importación activa y luego lo que la vista necesite. */
    function requestFromActiveImport(requestNumber) {
        return apiRequest({ resource: 'active' }).then((result) => {
            state.importId = result.import_id;
            state.filters = result.filters;
            state.overview = result.overview;
            if (state.level === 'program') {
                return fetchProgram(requestNumber);
            }
            if (state.level === 'student') {
                if (!state.filters || !state.competencyOptions.length) {
                    return fetchOverview(requestNumber).then((overview) => {
                        configureFilters(ctx, overview);
                        return fetchStudent();
                    });
                }
                return fetchStudent();
            }
            if (state.page > 1 || state.year || state.simulation) {
                return fetchOverview(requestNumber);
            }
            return result.overview;
        });
    }

    // --- Vistas -----------------------------------------------------------

    function loadCurrentView() {
        const requestNumber = ++state.requestNumber;
        showState(elements, 'loading');
        const request = state.importId
            ? requestCurrentData(requestNumber)
            : requestFromActiveImport(requestNumber);

        request.then(() => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            showState(elements, 'content');
            renderCurrentData();
            updateUrl(state, true);
            if (state.level === 'global' && state.selectedProgramId) {
                loadSelectedProgram();
            }
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            if (state.level === 'global' && !state.importId && error.status === 404) {
                showState(elements, 'empty');
                return;
            }
            showError(error);
        });
    }

    function loadSelectedProgram() {
        if (!state.selectedProgramId || !state.importId) {
            state.selectedProgramRequest += 1;
            renderSelectedProgram(ctx, null);
            return;
        }
        const requestId = ++state.selectedProgramRequest;
        renderSelectedProgram(ctx, null);
        apiRequest(Object.assign({
            resource: 'program',
            import_id: state.importId,
            program_id: state.selectedProgramId,
            page: 1
        }, buildFilterParams(state))).then((program) => {
            if (requestId === state.selectedProgramRequest &&
                state.level === 'global' &&
                state.selectedProgramId === program.program.program_id) {
                renderSelectedProgram(ctx, program);
            }
        }).catch((error) => {
            if (requestId !== state.selectedProgramRequest) {
                return;
            }
            if (error.status !== 404) {
                setText(root, '[data-error-message]', errorMessage(error));
            }
            renderSelectedProgram(ctx, null);
        });
    }

    function loadProgramStudents() {
        window.clearTimeout(state.searchTimer);
        const requestNumber = ++state.requestNumber;
        const status = root.querySelector('[data-student-search-status]');
        status.textContent = state.studentSearch ? 'Buscando…' : 'Cargando resultados…';
        fetchProgram(requestNumber).then((program) => {
            if (requestNumber !== state.requestNumber || state.level !== 'program') {
                return;
            }
            renderProgramStudents(ctx, program);
            status.textContent = state.studentSearch ? 'Búsqueda activa' : '';
            updateUrl(state, true);
        }).catch((error) => {
            if (requestNumber !== state.requestNumber || state.level !== 'program') {
                return;
            }
            status.textContent = errorMessage(error);
        });
    }

    // --- Navegación -------------------------------------------------------

    function openProgram(programId) {
        window.clearTimeout(state.searchTimer);
        state.level = 'program';
        state.programId = String(programId);
        state.page = 1;
        state.studentSearch = '';
        state.studentRef = '';
        state.program = null;
        updateUrl(state, false);
        loadCurrentView();
    }

    function openStudent(documentNumber) {
        ++state.requestNumber;
        window.clearTimeout(state.searchTimer);
        showState(elements, 'loading');
        apiRequest({ resource: 'student' }, {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                'X-Dashboard-Request': '1',
                'X-CSRF-Token': root.dataset.csrfToken
            },
            body: JSON.stringify({
                import_id: state.importId,
                document: documentNumber
            })
        }).then((student) => {
            state.student = student;
            state.studentRef = student.student_ref;
            state.level = 'student';
            updateUrl(state, false);
            showState(elements, 'content');
            renderCurrentData();
        }).catch(showError);
    }

    // --- Filtros y paginación ---------------------------------------------

    function changeFilters() {
        state.year = elements.yearFilter.value;
        state.simulation = elements.simulationFilter.value;
        state.subject = elements.subjectFilter.value;
        state.page = 1;
        updateFilterContext(ctx);
        updateUrl(state, true);
        if (state.level === 'student' && state.student) {
            renderStudent(ctx, state.student);
            return;
        }
        loadCurrentView();
    }

    function changeSubject() {
        state.subject = elements.subjectFilter.value;
        updateFilterContext(ctx);
        updateUrl(state, true);
        renderCurrentData();
        if (state.level === 'global' && state.selectedProgramId) {
            loadSelectedProgram();
        }
    }

    function changeSelectedProgram() {
        state.selectedProgramId = elements.programFilter.value;
        updateUrl(state, true);
        if (state.selectedProgramId) {
            loadSelectedProgram();
        } else {
            renderSelectedProgram(ctx, null);
        }
    }

    function resetFilters() {
        state.year = '';
        state.simulation = '';
        state.subject = 'global';
        state.page = 1;
        state.studentSearch = '';
        state.selectedProgramId = '';
        elements.yearFilter.value = '';
        elements.simulationFilter.value = '';
        elements.subjectFilter.value = 'global';
        elements.programFilter.value = '';
        elements.studentSearch.value = '';
        updateUrl(state, true);
        loadCurrentView();
    }

    function changeGlobalPage(delta) {
        const programs = state.overview ? state.overview.programs || [] : [];
        const totalPages = Math.max(1, Math.ceil(programs.length / PROGRAMS_PER_PAGE));
        const nextPage = state.page + delta;
        if (nextPage < 1 || nextPage > totalPages) {
            return;
        }
        state.page = nextPage;
        updateUrl(state, true);
        renderOverview(ctx, state.overview, false);
    }

    function changeStudentPage(delta) {
        const totalPages = state.program ? state.program.total_pages : 1;
        const nextPage = state.page + delta;
        if (nextPage < 1 || nextPage > totalPages) {
            return;
        }
        state.page = nextPage;
        updateUrl(state, true);
        loadProgramStudents();
    }

    /** Búsqueda de estudiantes con espera de 300 ms mientras se escribe. */
    function searchStudents(text) {
        state.studentSearch = text;
        state.page = 1;
        ++state.requestNumber;
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(loadProgramStudents, 300);
    }

    ctx.actions.openProgram = openProgram;
    ctx.actions.openStudent = openStudent;
    ctx.actions.loadSelectedProgram = loadSelectedProgram;

    return {
        loadCurrentView,
        changeFilters,
        changeSubject,
        changeSelectedProgram,
        resetFilters,
        changeGlobalPage,
        changeStudentPage,
        searchStudents
    };
}
