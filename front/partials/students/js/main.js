// Módulo Estudiantes (fase 13a): estudiantes de los Excel por nivel.
//
// Periodo como en el dashboard: Año → Periodo del año; al entrar, el último
// periodo con datos. "Todo el histórico" muestra a todos con el nivel de su
// periodo más reciente con puntajes.
//
// Las 5 tarjetas (Nivel 1–4 y Sin resultado) son los grupos: al pulsar una, la
// lista queda solo con ese grupo (sin cambiar el periodo); al pulsarla otra
// vez, se ven todos. La búsqueda y el programa son filtros extra.

import { apiRequest, errorMessage } from '../../shared/js/api.js';
import { addCell, populateSelect, setText } from '../../shared/js/dom.js';
import { formatNumber, parsePositiveInteger } from '../../shared/js/format.js';
import { semestersOf, splitPeriod, yearsOf } from '../../shared/js/periods.js';

const COMPETENCIES = ['lectura_critica', 'competencias_ciudadanas', 'razonamiento_cuantitativo', 'ingles'];
const LEVEL_KEYS = ['1', '2', '3', '4', 'sin-resultado'];
const SEARCH_DELAY_MS = 350;
const ALL_PERIODS = 'all';

const root = document.querySelector('[data-students]');

if (root) {
    const elements = {
        total: root.querySelector('[data-students-total]'),
        year: root.querySelector('[data-students-year]'),
        semester: root.querySelector('[data-students-semester]'),
        reset: root.querySelector('[data-students-reset]'),
        groups: Array.from(root.querySelectorAll('[data-level-group]')),
        search: root.querySelector('[data-students-search]'),
        program: root.querySelector('[data-students-program]'),
        context: root.querySelector('[data-students-context]'),
        clear: root.querySelector('[data-students-clear]'),
        loading: root.querySelector('[data-students-loading]'),
        errorBox: root.querySelector('[data-students-error]'),
        empty: root.querySelector('[data-students-empty]'),
        content: root.querySelector('[data-students-content]'),
        rows: root.querySelector('[data-students-rows]'),
        pagination: root.querySelector('[data-students-pagination]'),
        prev: root.querySelector('[data-students-prev]'),
        next: root.querySelector('[data-students-next]'),
        rule: root.querySelector('[data-students-rule]')
    };
    const initialLevel = root.dataset.level || '';
    const state = {
        // '' = el último periodo (lo decide la API); 'all' = todo el histórico.
        period: root.dataset.period || '',
        periods: [],
        level: LEVEL_KEYS.includes(initialLevel) ? initialLevel : '',
        programId: root.dataset.programId || '',
        search: root.dataset.search || '',
        page: parsePositiveInteger(new URL(window.location.href).searchParams.get('page'), 1),
        requestNumber: 0,
        searchTimer: null
    };
    elements.search.value = state.search;

    const show = (name) => {
        elements.loading.hidden = name !== 'loading';
        elements.errorBox.hidden = name !== 'error';
        elements.empty.hidden = name !== 'empty';
        elements.content.hidden = name !== 'content';
    };

    const updateUrl = () => {
        const url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'students');
        if (state.period) url.searchParams.set('period', state.period);
        if (state.level) url.searchParams.set('level', state.level);
        if (state.programId) url.searchParams.set('program_id', state.programId);
        if (state.search) url.searchParams.set('search', state.search);
        if (state.page > 1) url.searchParams.set('page', String(state.page));
        window.history.replaceState({}, '', url);
    };

    const studentsText = (count) => formatNumber(count) + (count === 1 ? ' estudiante' : ' estudiantes');
    const groupLabel = (key) => (key === 'sin-resultado' ? 'Sin resultado' : 'Nivel ' + key);

    const periodLabel = (period) => (period === ALL_PERIODS ? 'Todo el histórico' : 'Periodo ' + period);

    /** Año y periodo del año, en cascada; "Todo el histórico" va al final de los años. */
    const fillPeriodFilters = (response) => {
        const years = yearsOf(response.periods).map((year) => ({ value: year, label: year }));
        years.push({ value: ALL_PERIODS, label: 'Todo el histórico' });
        if (response.period === ALL_PERIODS) {
            populateSelect(elements.year, years, ALL_PERIODS, null);
            populateSelect(elements.semester, [{ value: '', label: 'Todos los periodos' }], '', null);
            elements.semester.disabled = true;
            return;
        }
        const current = splitPeriod(response.period) || { year: '', semester: '' };
        populateSelect(elements.year, years, current.year, null);
        populateSelect(
            elements.semester,
            semestersOf(response.periods, current.year).map((semester) => ({
                value: semester,
                label: 'Periodo ' + semester + ' (' + current.year + '-' + semester + ')'
            })),
            current.semester,
            null
        );
        elements.semester.disabled = false;
    };

    const renderGroups = (response) => {
        const counts = {};
        response.groups.forEach((group) => { counts[group.key] = group.count; });
        elements.groups.forEach((button) => {
            const key = button.dataset.levelGroup;
            const count = counts[key] || 0;
            setText(button, '[data-level-count]', formatNumber(count));
            setText(button, '[data-level-share]', response.total
                ? formatNumber(Math.round(count * 1000 / response.total) / 10) + ' %'
                : '0 %');
            const active = state.level === key;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        root.classList.toggle('has-level', Boolean(state.level));
    };

    const levelBadge = (level) => {
        const badge = document.createElement('span');
        const key = level === null || level === undefined ? 'sin-resultado' : String(level);
        badge.className = 'level-badge level-badge-' + key;
        badge.textContent = key === 'sin-resultado' ? 'Sin resultado' : 'N' + key;
        return badge;
    };

    const renderRows = (students) => {
        elements.rows.replaceChildren();
        students.forEach((student) => {
            const row = document.createElement('tr');

            const person = document.createElement('td');
            const name = document.createElement('strong');
            name.textContent = student.name || 'Nombre no disponible';
            const email = document.createElement('small');
            email.textContent = student.email || 'Sin correo';
            person.append(name, email);
            person.className = 'students-person';
            row.appendChild(person);

            addCell(row, student.document
                ? (student.document_type ? student.document_type + ' ' : '') + student.document
                : 'Sin documento');
            addCell(row, student.program, student.program_id === 'sin-programa' ? 'is-sin-programa' : '');

            const levelCell = document.createElement('td');
            levelCell.appendChild(levelBadge(student.level));
            row.appendChild(levelCell);

            COMPETENCIES.forEach((key) => {
                const value = student.competency_levels[key];
                addCell(row, value || '—', 'students-competency');
            });
            addCell(row, student.average === null ? '—' : formatNumber(Math.round(student.average * 10) / 10));
            addCell(row, student.level_period
                ? student.level_period + ' · ' + student.level_sources.join(' + ')
                : 'Último: ' + (student.last_period || '—'), 'students-source');
            elements.rows.appendChild(row);
        });
    };

    const renderContext = (response) => {
        const parts = [periodLabel(response.period)];
        parts.push(state.level ? groupLabel(state.level) : 'Todos los niveles');
        if (state.programId) {
            const program = response.programs.find((item) => item.program_id === state.programId);
            parts.push(program ? program.name : 'Programa elegido');
        }
        if (state.search) {
            parts.push('“' + state.search + '”');
        }
        elements.context.textContent = parts.join(' · ') + ' — ' + studentsText(response.filtered_total);
        elements.clear.hidden = !state.level;
    };

    const renderPagination = (response) => {
        const pages = Math.max(1, Math.ceil(response.filtered_total / response.page_size));
        elements.pagination.hidden = pages <= 1;
        elements.prev.disabled = response.page <= 1;
        elements.next.disabled = response.page >= pages;
        elements.pagination.querySelector('[data-students-page]').textContent =
            'Página ' + response.page + ' de ' + pages;
    };

    const load = () => {
        const requestNumber = ++state.requestNumber;
        show('loading');
        apiRequest({
            resource: 'students',
            period: state.period,
            level: state.level,
            program_id: state.programId,
            search: state.search,
            page: state.page
        }).then((response) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            if (state.period && state.period !== ALL_PERIODS && !response.periods.includes(state.period)) {
                // Periodo sin datos (por ejemplo, un enlace viejo): se usa el último.
                state.period = '';
                load();
                return;
            }
            // Desde aquí el periodo queda fijo: cambiar de nivel no lo devuelve al último.
            state.period = response.period;
            state.periods = response.periods;
            fillPeriodFilters(response);
            const pages = Math.max(1, Math.ceil(response.filtered_total / response.page_size));
            if (state.page > pages) {
                // La página pedida ya no existe con estos filtros.
                state.page = pages;
                load();
                return;
            }
            const programs = response.programs.map((item) => ({ value: item.program_id, label: item.name }));
            if (!populateSelect(elements.program, programs, state.programId, 'Todos los programas') && state.programId) {
                state.programId = '';
                load();
                return;
            }
            elements.total.textContent = studentsText(response.total);
            elements.rule.textContent = response.rule;
            renderGroups(response);
            renderContext(response);
            updateUrl();

            if (!response.students.length) {
                const nobody = response.total === 0 && !state.search && !state.programId;
                setText(root, '[data-students-empty-title]', nobody
                    ? 'Aún no hay estudiantes'
                    : 'No hay estudiantes con estos filtros');
                setText(root, '[data-students-empty-copy]', nobody
                    ? 'Los estudiantes aparecen aquí al importar los Excel de ESE o de CORHUILA.'
                    : 'Prueba con otro nivel, otro programa u otra búsqueda.');
                show('empty');
                return;
            }
            renderRows(response.students);
            renderPagination(response);
            show('content');
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-students-error-message]', errorMessage(error));
            show('error');
        });
    };

    const reload = () => {
        state.page = 1;
        load();
    };

    // Cambiar de año elige el periodo más reciente de ese año (como el dashboard).
    elements.year.addEventListener('change', () => {
        const year = elements.year.value;
        if (year === ALL_PERIODS) {
            state.period = ALL_PERIODS;
        } else {
            const semester = semestersOf(state.periods, year)[0];
            state.period = semester ? year + '-' + semester : '';
        }
        reload();
    });
    elements.semester.addEventListener('change', () => {
        state.period = elements.year.value + '-' + elements.semester.value;
        reload();
    });
    elements.reset.addEventListener('click', () => {
        state.period = '';
        reload();
    });
    elements.groups.forEach((button) => {
        button.addEventListener('click', () => {
            const key = button.dataset.levelGroup;
            state.level = state.level === key ? '' : key;
            reload();
        });
    });
    elements.clear.addEventListener('click', () => {
        state.level = '';
        reload();
    });
    elements.program.addEventListener('change', () => {
        state.programId = elements.program.value;
        reload();
    });
    elements.search.addEventListener('input', () => {
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => {
            const value = elements.search.value.trim();
            if (value !== state.search) {
                state.search = value;
                reload();
            }
        }, SEARCH_DELAY_MS);
    });
    elements.prev.addEventListener('click', () => {
        state.page = Math.max(1, state.page - 1);
        load();
    });
    elements.next.addEventListener('click', () => {
        state.page += 1;
        load();
    });
    root.querySelector('[data-students-retry]').addEventListener('click', load);

    load();
}
