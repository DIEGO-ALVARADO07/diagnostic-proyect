// Matriculados (fase 14a): archivo oficial de estudiantes por periodo.
//
// Arranca en el periodo más reciente cargado. Los filtros (programa, semestre,
// tipo de documento, género y estrato) salen del propio archivo y se guardan en
// la URL; cambiar de periodo los quita. Solo lo ve el administrador.

import { apiRequest, errorMessage } from '../../shared/js/api.js';
import { populateSelect, setText } from '../../shared/js/dom.js';
import { formatNumber, parsePositiveInteger } from '../../shared/js/format.js';

const SEARCH_DELAY_MS = 350;
const FILTERS = [
    { key: 'program', data: 'program', options: 'programs', all: 'Todos los programas' },
    { key: 'semester', data: 'semester', options: 'semesters', all: 'Todos los semestres' },
    { key: 'document_type', data: 'documentType', options: 'document_types', all: 'Todos los tipos' },
    { key: 'gender', data: 'gender', options: 'genders', all: 'Todos' },
    { key: 'stratum', data: 'stratum', options: 'strata', all: 'Todos los estratos' }
];
const SELECTORS = {
    program: '[data-enrollment-program]',
    semester: '[data-enrollment-semester]',
    document_type: '[data-enrollment-document-type]',
    gender: '[data-enrollment-gender]',
    stratum: '[data-enrollment-stratum]'
};

const root = document.querySelector('[data-enrollment]');

if (root) {
    const $ = (selector) => root.querySelector(selector);
    const elements = {
        total: $('[data-enrollment-total]'),
        uploads: $('[data-enrollment-uploads]'),
        uploadCards: $('[data-enrollment-upload-cards]'),
        filtersPanel: $('[data-enrollment-filters]'),
        period: $('[data-enrollment-period]'),
        reset: $('[data-enrollment-reset]'),
        search: $('[data-enrollment-search]'),
        context: $('[data-enrollment-context]'),
        loading: $('[data-enrollment-loading]'),
        errorBox: $('[data-enrollment-error]'),
        empty: $('[data-enrollment-empty]'),
        content: $('[data-enrollment-content]'),
        rows: $('[data-enrollment-rows]'),
        pagination: $('[data-enrollment-pagination]'),
        prev: $('[data-enrollment-prev]'),
        next: $('[data-enrollment-next]')
    };
    const selects = {};
    Object.keys(SELECTORS).forEach((key) => { selects[key] = $(SELECTORS[key]); });

    const state = {
        period: /^\d{4}-[12]$/.test(root.dataset.period || '') ? root.dataset.period : '',
        filters: {},
        search: root.dataset.search || '',
        page: parsePositiveInteger(new URL(window.location.href).searchParams.get('page'), 1),
        requestNumber: 0,
        searchTimer: null
    };
    FILTERS.forEach((filter) => { state.filters[filter.key] = root.dataset[filter.data] || ''; });
    elements.search.value = state.search;

    const show = (name) => {
        elements.loading.hidden = name !== 'loading';
        elements.errorBox.hidden = name !== 'error';
        elements.empty.hidden = name !== 'empty';
        elements.content.hidden = name !== 'content';
    };

    const plural = (count, one, many) => formatNumber(count) + ' ' + (count === 1 ? one : many);

    const formatDateTime = (value) => {
        if (!value) {
            return '—';
        }
        const date = new Date(value.endsWith('Z') ? value : value + 'Z');
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
    };

    const formatBirthDate = (value) => {
        if (!value) {
            return '—';
        }
        const parts = value.split('-');
        return parts.length === 3 ? parts[2] + '/' + parts[1] + '/' + parts[0] : value;
    };

    const updateUrl = () => {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'enrollment');
        if (state.period) url.searchParams.set('period', state.period);
        FILTERS.forEach((filter) => {
            if (state.filters[filter.key]) url.searchParams.set(filter.key, state.filters[filter.key]);
        });
        if (state.search) url.searchParams.set('search', state.search);
        if (state.page > 1) url.searchParams.set('page', String(state.page));
        window.history.replaceState({}, '', url);
    };

    const node = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    };

    const cell = (row, value, className) => {
        const td = node('td', className, value === null || value === undefined || value === '' ? '—' : String(value));
        row.appendChild(td);
        return td;
    };

    const renderUploads = (uploads, period) => {
        elements.uploadCards.replaceChildren();
        uploads.forEach((upload) => {
            const card = node('article', 'enrollment-upload-card' + (upload.period === period ? ' is-current' : ''));
            card.append(
                node('strong', 'enrollment-upload-period', upload.period),
                node('span', 'enrollment-upload-file', upload.filename),
                node('span', 'enrollment-upload-stats',
                    plural(upload.students, 'estudiante', 'estudiantes') + ' · ' +
                    plural(upload.rows, 'fila', 'filas') + ' · ' +
                    plural(upload.double_program, 'en doble programa', 'en doble programa')),
                node('small', '', 'Subido por ' + (upload.uploaded_by || 'usuario no disponible') + ' · ' + formatDateTime(upload.uploaded_at))
            );
            elements.uploadCards.appendChild(card);
        });
        elements.uploads.hidden = uploads.length === 0;
    };

    const renderFilters = (response) => {
        populateSelect(
            elements.period,
            response.uploads.map((upload) => ({ value: upload.period, label: 'Periodo ' + upload.period })),
            response.period || '',
            null
        );
        FILTERS.forEach((filter) => {
            const options = response.filters[filter.options].map((option) => ({
                value: option.value,
                label: option.label + ' (' + formatNumber(option.count) + ')'
            }));
            const available = populateSelect(selects[filter.key], options, state.filters[filter.key], filter.all);
            if (!available) {
                state.filters[filter.key] = '';
            }
        });
        elements.filtersPanel.hidden = response.uploads.length === 0;
    };

    const renderRows = (items) => {
        elements.rows.replaceChildren();
        items.forEach((item) => {
            const row = document.createElement('tr');

            const student = node('td', 'enrollment-student');
            student.append(
                node('strong', '', [item.last_names, item.first_names].filter(Boolean).join(' ') || '—'),
                node('small', '', item.student_code ? 'Código ' + item.student_code : 'Sin código')
            );
            row.appendChild(student);

            const documentCell = node('td', 'enrollment-document');
            documentCell.append(
                node('span', 'enrollment-doc-type', item.document_type || '—'),
                document.createTextNode(' ' + item.document_number)
            );
            row.appendChild(documentCell);

            const program = node('td', 'enrollment-program');
            program.append(node('span', '', item.program));
            if (item.pensum_code) {
                program.append(node('small', '', 'Pensum ' + item.pensum_code));
            }
            if (item.programs_count > 1) {
                program.append(node('span', 'enrollment-double', item.programs_count + ' programas'));
            }
            row.appendChild(program);

            cell(row, item.semester, 'enrollment-center');
            cell(row, item.institutional_email, 'enrollment-email');
            cell(row, item.personal_email, 'enrollment-email');
            cell(row, item.phone);
            cell(row, item.mobile);
            cell(row, item.gender, 'enrollment-center');
            cell(row, item.stratum, 'enrollment-center');
            cell(row, formatBirthDate(item.birth_date));
            elements.rows.appendChild(row);
        });
    };

    const renderContext = (response) => {
        const active = FILTERS.filter((filter) => state.filters[filter.key]).length + (state.search ? 1 : 0);
        elements.context.textContent = 'Periodo ' + response.period + ': ' +
            plural(response.filtered_total, 'fila', 'filas') + ' · ' +
            plural(response.filtered_students, 'estudiante', 'estudiantes') +
            (active ? ' con los filtros elegidos' : '');
    };

    const render = (response) => {
        renderUploads(response.uploads, response.period);
        renderFilters(response);
        const current = response.uploads.find((upload) => upload.period === response.period);
        elements.total.textContent = current ? plural(current.students, 'estudiante', 'estudiantes') : '— estudiantes';

        if (!response.uploads.length) {
            setText(root, '[data-enrollment-empty-title]', 'Todavía no hay matriculados');
            setText(root, '[data-enrollment-empty-copy]', 'Sube el archivo de matriculados del periodo para empezar. Sin él, CORHUILA no puede tomar el programa ni el semestre de los estudiantes.');
            elements.context.textContent = '';
            show('empty');
            return;
        }
        if (!response.items.length) {
            setText(root, '[data-enrollment-empty-title]', 'Ningún matriculado coincide');
            setText(root, '[data-enrollment-empty-copy]', 'Cambia los filtros o la búsqueda.');
            renderContext(response);
            show('empty');
            return;
        }
        renderRows(response.items);
        renderContext(response);
        const pages = Math.max(1, Math.ceil(response.filtered_total / response.page_size));
        state.page = response.page;
        elements.pagination.hidden = pages <= 1;
        elements.prev.disabled = response.page <= 1;
        elements.next.disabled = response.page >= pages;
        setText(elements.pagination, '[data-enrollment-page]', 'Página ' + response.page + ' de ' + pages);
        show('content');
    };

    const load = () => {
        const requestNumber = ++state.requestNumber;
        show('loading');
        const params = { resource: 'enrollment', period: state.period, search: state.search, page: state.page };
        FILTERS.forEach((filter) => { params[filter.key] = state.filters[filter.key]; });
        return apiRequest(params).then((response) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            state.period = response.period || '';
            render(response);
            updateUrl();
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-enrollment-error-message]', errorMessage(error));
            show('error');
        });
    };

    const clearFilters = () => {
        FILTERS.forEach((filter) => { state.filters[filter.key] = ''; });
        state.search = '';
        elements.search.value = '';
    };

    elements.period.addEventListener('change', () => {
        state.period = elements.period.value;
        clearFilters();
        state.page = 1;
        load();
    });
    FILTERS.forEach((filter) => {
        selects[filter.key].addEventListener('change', () => {
            state.filters[filter.key] = selects[filter.key].value;
            state.page = 1;
            load();
        });
    });
    elements.search.addEventListener('input', () => {
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => {
            state.search = elements.search.value.trim();
            state.page = 1;
            load();
        }, SEARCH_DELAY_MS);
    });
    elements.reset.addEventListener('click', () => {
        clearFilters();
        state.page = 1;
        load();
    });
    elements.prev.addEventListener('click', () => {
        state.page = Math.max(1, state.page - 1);
        load();
    });
    elements.next.addEventListener('click', () => {
        state.page += 1;
        load();
    });
    $('[data-enrollment-retry]').addEventListener('click', load);

    load();
}
