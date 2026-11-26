// Estado del dashboard y su reflejo en la URL.

import { parsePositiveInteger } from '../../shared/js/format.js';

export const PROGRAMS_PER_PAGE = 6;

const LEVELS = ['global', 'program', 'student'];

/** Estado inicial, tomado de los data-* que pinta screen.php. */
export function createState(root) {
    return {
        level: root.dataset.level || 'global',
        importId: root.dataset.importId || '',
        programId: root.dataset.programId || '',
        studentRef: root.dataset.studentRef || '',
        year: root.dataset.year || '',
        period: root.dataset.period || '',
        moment: root.dataset.moment || '',
        subject: root.dataset.subject || 'global',
        page: parsePositiveInteger(root.dataset.page, 1),
        studentSearch: '',
        overview: null,
        program: null,
        student: null,
        filters: null,
        competencyOptions: [],
        selectedProgramId: '',
        programFilterData: null,
        requestNumber: 0,
        selectedProgramRequest: 0,
        searchTimer: null
    };
}

export function readUrlState(state) {
    const params = new URLSearchParams(window.location.search);
    state.level = params.get('level') || 'global';
    state.importId = params.get('import_id') || '';
    state.programId = params.get('program_id') || '';
    state.studentRef = params.get('student_ref') || '';
    state.year = params.get('year') || '';
    state.period = params.get('period') || '';
    state.moment = params.get('moment') || '';
    state.subject = params.get('subject') || 'global';
    state.page = parsePositiveInteger(params.get('page'), 1);
    state.studentSearch = params.get('search') || '';
    state.selectedProgramId = params.get('program_filter') || '';
    if (!LEVELS.includes(state.level)) {
        state.level = 'global';
    }
}

export function buildFilterParams(state) {
    return {
        year: state.year,
        period: state.period,
        moment: state.moment
    };
}

export function dashboardUrl(state) {
    const url = new URL('index.php', window.location.href);
    url.searchParams.set('view', 'ese');
    url.searchParams.set('level', state.level);
    if (state.importId) {
        url.searchParams.set('import_id', state.importId);
    }
    if (state.year) {
        url.searchParams.set('year', state.year);
    }
    if (state.period) {
        url.searchParams.set('period', state.period);
    }
    if (state.moment) {
        url.searchParams.set('moment', state.moment);
    }
    if (state.subject && state.subject !== 'global') {
        url.searchParams.set('subject', state.subject);
    }

    if (state.level === 'program' || state.level === 'student') {
        url.searchParams.set('program_id', state.programId);
        url.searchParams.set('page', String(state.page));
    } else {
        if (state.page > 1) {
            url.searchParams.set('page', String(state.page));
        }
        if (state.selectedProgramId) {
            url.searchParams.set('program_filter', state.selectedProgramId);
        }
    }
    if (state.studentSearch) {
        url.searchParams.set('search', state.studentSearch);
    }
    if (state.level === 'student' && state.studentRef) {
        url.searchParams.set('student_ref', state.studentRef);
    }
    return url;
}

export function updateUrl(state, replace) {
    const url = dashboardUrl(state);
    if (replace) {
        window.history.replaceState({}, '', url);
    } else {
        window.history.pushState({}, '', url);
    }
}

export function dashboardUrlForProgram(state, programId) {
    const url = dashboardUrl(state);
    url.searchParams.set('level', 'program');
    url.searchParams.set('program_id', programId);
    url.searchParams.delete('program_filter');
    url.searchParams.delete('page');
    url.searchParams.delete('search');
    url.searchParams.delete('student_ref');
    return url.toString();
}

export function dashboardUrlForGlobal(state) {
    const url = dashboardUrl(state);
    url.searchParams.set('level', 'global');
    url.searchParams.delete('program_id');
    url.searchParams.delete('student_ref');
    url.searchParams.delete('search');
    url.searchParams.delete('page');
    return url.toString();
}
