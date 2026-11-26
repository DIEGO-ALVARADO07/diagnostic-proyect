// Panel del administrador: cursos eliminados con toda su información y "Habilitar".

import { apiPost, apiRequest, errorMessage } from '../../shared/js/api.js';
import { confirmAction } from '../../shared/js/confirm.js';
import { setText } from '../../shared/js/dom.js';
import { formatNumber } from '../../shared/js/format.js';

const root = document.querySelector('[data-courses-deleted]');

if (root) {
    const elements = {
        total: root.querySelector('[data-deleted-total]'),
        status: root.querySelector('[data-deleted-status]'),
        loading: root.querySelector('[data-deleted-loading]'),
        errorBox: root.querySelector('[data-deleted-error]'),
        empty: root.querySelector('[data-deleted-empty]'),
        content: root.querySelector('[data-deleted-content]'),
        rows: root.querySelector('[data-deleted-rows]')
    };
    const csrfToken = root.dataset.csrfToken;
    const plural = (count, one, many) => formatNumber(count) + ' ' + (count === 1 ? one : many);

    const show = (name) => {
        elements.loading.hidden = name !== 'loading';
        elements.errorBox.hidden = name !== 'error';
        elements.empty.hidden = name !== 'empty';
        elements.content.hidden = name !== 'content';
    };

    const setStatus = (message, isError) => {
        elements.status.textContent = message || '';
        elements.status.classList.toggle('is-error', Boolean(isError));
    };

    const formatDate = (value) => {
        if (!value) {
            return '—';
        }
        // La API guarda UTC sin zona; se muestra en la hora local.
        const date = new Date(value.endsWith('Z') ? value : value + 'Z');
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString('es-CO', {
            dateStyle: 'medium', timeStyle: 'short'
        });
    };

    const cell = (row, className) => {
        const td = document.createElement('td');
        if (className) {
            td.className = className;
        }
        row.appendChild(td);
        return td;
    };

    const text = (tag, className, value) => {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        node.textContent = value;
        return node;
    };

    const audit = (td, who, when) => {
        td.append(text('strong', '', who || 'Usuario no disponible'), text('small', '', formatDate(when)));
    };

    const render = (courses) => {
        elements.total.textContent = plural(courses.length, 'curso', 'cursos');
        elements.rows.replaceChildren();
        courses.forEach((course) => {
            const row = document.createElement('tr');
            const name = cell(row, 'deleted-course-name');
            name.append(text('span', 'course-subject', course.competency_label), text('strong', '', course.name));

            const level = cell(row);
            const badge = text('span', 'level-badge level-badge-' + course.level, 'N' + course.level);
            level.appendChild(badge);

            cell(row, 'deleted-course-text').textContent = course.description;
            cell(row, 'deleted-course-text').textContent = course.methodology;
            cell(row, 'deleted-course-count').textContent = formatNumber(course.students);
            audit(cell(row, 'deleted-course-audit'), course.created_by, course.created_at);
            audit(cell(row, 'deleted-course-audit'), course.deleted_by, course.deleted_at);

            const action = cell(row, 'deleted-course-action');
            const enable = text('button', 'button button-primary', '⟲ Habilitar');
            enable.type = 'button';
            enable.addEventListener('click', () => restore(course, enable));
            action.appendChild(enable);
            elements.rows.appendChild(row);
        });
        show(courses.length ? 'content' : 'empty');
    };

    const load = () => {
        show('loading');
        return apiRequest({ resource: 'courses_deleted' }).then((result) => render(result.courses)).catch((error) => {
            setText(root, '[data-deleted-error-message]', errorMessage(error));
            show('error');
        });
    };

    async function restore(course, control) {
        const ok = await confirmAction({
            title: '¿Habilitar este curso?',
            message: 'Vuelve a Cursos, en su nivel, con los mismos estudiantes. Queda registrado que tú lo habilitaste.',
            details: [
                ['Curso', course.name],
                ['Materia', course.competency_label],
                ['Nivel', 'Nivel ' + course.level],
                ['Estudiantes', formatNumber(course.students)],
                ['Eliminado por', (course.deleted_by || 'Usuario no disponible') + ' · ' + formatDate(course.deleted_at)]
            ],
            confirmLabel: 'Habilitar curso',
            tone: 'primary'
        });
        if (!ok) {
            return;
        }
        control.disabled = true;
        apiPost('course_restore', { course_id: course.id }, csrfToken).then((restored) => {
            setStatus('Se habilitó "' + restored.name + '" en el Nivel ' + restored.level + ' (' +
                restored.competency_label + ') con sus ' + plural(restored.students, 'estudiante', 'estudiantes') + '.');
            return load();
        }).catch((error) => {
            setStatus(errorMessage(error), true);
            control.disabled = false;
        });
    }

    root.querySelector('[data-deleted-retry]').addEventListener('click', load);

    load();
}
