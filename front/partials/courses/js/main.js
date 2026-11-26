// Módulo Cursos (fase 13b): Nivel → Curso → Estudiantes.
//
// Se ven los 4 niveles. Al abrir uno aparecen sus cursos, cada uno con su
// materia, descripción y metodología, y con "Agregar estudiantes" (los que
// tienen ese nivel en esa materia, en el periodo elegido arriba), "Ver
// estudiantes" y "Eliminar" (lógico; solo el administrador los habilita de
// nuevo, desde "Cursos eliminados").

import { apiPost, apiRequest, errorMessage } from '../../shared/js/api.js';
import { confirmAction } from '../../shared/js/confirm.js';
import { addCell, populateSelect, setText } from '../../shared/js/dom.js';
import { formatNumber } from '../../shared/js/format.js';

const ALL_PERIODS = 'all';
const root = document.querySelector('[data-courses]');

if (root) {
    const elements = {
        total: root.querySelector('[data-courses-total]'),
        form: root.querySelector('[data-course-form]'),
        name: root.querySelector('[data-course-name]'),
        level: root.querySelector('[data-course-level]'),
        competency: root.querySelector('[data-course-competency]'),
        description: root.querySelector('[data-course-description]'),
        methodology: root.querySelector('[data-course-methodology]'),
        submit: root.querySelector('[data-course-submit]'),
        status: root.querySelector('[data-courses-status]'),
        period: root.querySelector('[data-courses-period]'),
        loading: root.querySelector('[data-courses-loading]'),
        errorBox: root.querySelector('[data-courses-error]'),
        content: root.querySelector('[data-courses-content]'),
        sections: Array.from(root.querySelectorAll('[data-course-level-section]'))
    };
    const state = {
        csrfToken: root.dataset.csrfToken,
        data: null,
        period: '',
        openLevels: new Set(),
        openCourses: new Set(),
        students: new Map(),
        requestNumber: 0
    };

    const plural = (count, one, many) => formatNumber(count) + ' ' + (count === 1 ? one : many);
    const periodLabel = (period) => (period === ALL_PERIODS ? 'todo el histórico' : period);

    const setStatus = (message, isError) => {
        elements.status.textContent = message || '';
        elements.status.classList.toggle('is-error', Boolean(isError));
    };

    const show = (name) => {
        elements.loading.hidden = name !== 'loading';
        elements.errorBox.hidden = name !== 'error';
        elements.content.hidden = name !== 'content';
    };

    const levelBadge = (level) => {
        const badge = document.createElement('span');
        const key = level === null || level === undefined ? 'sin-resultado' : String(level);
        badge.className = 'level-badge level-badge-' + key;
        badge.textContent = key === 'sin-resultado' ? 'Sin resultado' : 'N' + key;
        return badge;
    };

    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    };

    const button = (label, className, onClick) => {
        const node = element('button', className, label);
        node.type = 'button';
        node.addEventListener('click', onClick);
        return node;
    };

    // --- Estudiantes de un curso ---------------------------------------------

    const renderStudents = (container, course) => {
        container.replaceChildren();
        const result = state.students.get(course.id);
        if (!result) {
            container.textContent = 'Cargando estudiantes…';
            return;
        }
        if (result.error) {
            container.textContent = result.error;
            return;
        }
        if (!result.students.length) {
            container.appendChild(element('p', 'course-empty',
                'Este curso aún no tiene estudiantes. Usa "Agregar estudiantes".'));
            return;
        }
        const wrap = element('div', 'table-wrap');
        const table = element('table', 'students-table course-students-table');
        table.innerHTML = '<thead><tr><th>ESTUDIANTE</th><th>DOCUMENTO</th><th>PROGRAMA</th>' +
            '<th title="Nivel en la materia y periodo con los que se inscribió">AL INSCRIBIRSE</th>' +
            '<th title="Nivel actual en la materia (su periodo más reciente con puntajes)">NIVEL ACTUAL</th><th></th></tr></thead>';
        const body = document.createElement('tbody');
        result.students.forEach((student) => {
            const row = document.createElement('tr');
            const person = element('td', 'students-person');
            person.append(element('strong', '', student.name), element('small', '', student.email || 'Sin correo'));
            row.appendChild(person);
            addCell(row, student.document || 'Sin documento');
            addCell(row, student.program, student.program === 'Sin programa' ? 'is-sin-programa' : '');

            const enrolled = document.createElement('td');
            enrolled.append(levelBadge(student.enrolled_level),
                element('small', 'course-period', periodLabel(student.enrolled_period || '')));
            row.appendChild(enrolled);

            const current = document.createElement('td');
            current.appendChild(levelBadge(student.current_level));
            if (student.current_period) {
                current.appendChild(element('small', 'course-period', student.current_period));
            }
            row.appendChild(current);

            const actions = document.createElement('td');
            actions.appendChild(button('Quitar', 'course-link-danger', () => removeStudent(course, student)));
            row.appendChild(actions);
            body.appendChild(row);
        });
        table.appendChild(body);
        wrap.appendChild(table);
        container.appendChild(wrap);
    };

    const loadStudents = (course) => {
        state.students.delete(course.id);
        render();
        return apiRequest({ resource: 'course_students', course_id: course.id }).then((result) => {
            state.students.set(course.id, result);
        }).catch((error) => {
            state.students.set(course.id, { error: errorMessage(error) });
        }).then(render);
    };

    // --- Cursos ----------------------------------------------------------------

    const renderCourse = (course, levelData) => {
        const card = element('article', 'course-card');
        const open = state.openCourses.has(course.id);
        const available = levelData.available_students[course.competency] || 0;

        const header = element('div', 'course-card-header');
        const info = document.createElement('div');
        const title = element('h3');
        title.append(element('span', 'course-subject', course.competency_label), document.createTextNode(course.name));
        info.append(title, element('p', '',
            plural(course.students, 'estudiante inscrito', 'estudiantes inscritos') +
            (course.created_by ? ' · creado por ' + course.created_by : '')));

        const actions = element('div', 'course-card-actions');
        const enroll = button('＋ Agregar estudiantes', 'button button-primary', () => enrollCourse(course, enroll));
        enroll.title = 'Inscribe a los ' + plural(available, 'estudiante', 'estudiantes') +
            ' con Nivel ' + course.level + ' en ' + course.competency_label;
        actions.append(
            enroll,
            button(open ? 'Ocultar estudiantes' : 'Ver estudiantes', 'button button-secondary', () => toggleCourse(course)),
            button('Eliminar', 'course-link-danger', () => deleteCourse(course))
        );
        header.append(info, actions);
        card.appendChild(header);

        const details = element('dl', 'course-details');
        details.append(
            element('dt', '', 'Descripción'), element('dd', '', course.description),
            element('dt', '', 'Metodología'), element('dd', '', course.methodology)
        );
        card.appendChild(details);

        if (open) {
            const students = element('div', 'course-students');
            renderStudents(students, course);
            card.appendChild(students);
        }
        return card;
    };

    const renderAvailable = (container, levelData) => {
        container.replaceChildren();
        container.appendChild(element('span', 'course-available-title',
            'Estudiantes con este nivel en ' + state.data.period + ':'));
        state.data.competencies.forEach((competency) => {
            const chip = element('span', 'course-available-chip');
            chip.append(element('strong', '', formatNumber(levelData.available_students[competency.key] || 0)),
                document.createTextNode(' ' + competency.label));
            container.appendChild(chip);
        });
    };

    const render = () => {
        const data = state.data;
        if (!data) {
            return;
        }
        const totalCourses = data.levels.reduce((sum, level) => sum + level.courses.length, 0);
        elements.total.textContent = plural(totalCourses, 'curso', 'cursos');

        elements.sections.forEach((section) => {
            const levelNumber = Number(section.dataset.courseLevelSection);
            const levelData = data.levels.find((item) => item.level === levelNumber);
            const open = state.openLevels.has(levelNumber);
            const subjects = new Set(levelData.courses.map((course) => course.competency)).size;
            section.classList.toggle('is-open', open);
            section.querySelector('[data-course-level-toggle]').setAttribute('aria-expanded', open ? 'true' : 'false');
            setText(section, '[data-course-level-summary]',
                plural(levelData.courses.length, 'curso', 'cursos') + ' · ' +
                plural(subjects, 'materia', 'materias') + ' de 4');
            section.querySelector('[data-course-level-body]').hidden = !open;
            renderAvailable(section.querySelector('[data-course-level-available]'), levelData);
            const list = section.querySelector('[data-course-list]');
            list.replaceChildren();
            levelData.courses.forEach((course) => list.appendChild(renderCourse(course, levelData)));
            section.querySelector('[data-course-empty]').hidden = levelData.courses.length > 0;
        });
    };

    const fillPeriods = (data) => {
        const options = data.periods.map((period, index) => ({
            value: period,
            label: period + (index === 0 ? ' (último)' : '')
        }));
        options.push({ value: ALL_PERIODS, label: 'Todo el histórico' });
        if (!state.period) {
            state.period = data.period;
        }
        populateSelect(elements.period, options, state.period, null);
        state.period = elements.period.value;
    };

    const load = () => {
        const requestNumber = ++state.requestNumber;
        if (!state.data) {
            show('loading');
        }
        return apiRequest({ resource: 'courses' }).then((data) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            state.data = data;
            fillPeriods(data);
            render();
            show('content');
        }).catch((error) => {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            setText(root, '[data-courses-error-message]', errorMessage(error));
            show('error');
        });
    };

    // --- Acciones ----------------------------------------------------------------

    function toggleCourse(course) {
        if (state.openCourses.has(course.id)) {
            state.openCourses.delete(course.id);
            render();
            return;
        }
        state.openCourses.add(course.id);
        loadStudents(course);
    }

    function enrollCourse(course, control) {
        control.disabled = true;
        setStatus('Agregando a "' + course.name + '" los estudiantes con Nivel ' + course.level +
            ' en ' + course.competency_label + '…');
        apiPost('course_enroll', { course_id: course.id, period: state.period }, state.csrfToken).then((result) => {
            setStatus('"' + course.name + '": se agregaron ' + plural(result.added, 'estudiante', 'estudiantes') +
                (result.already_enrolled ? ' (' + formatNumber(result.already_enrolled) + ' ya estaban inscritos)' : '') +
                '. Nivel ' + course.level + ' en ' + course.competency_label + ' (' + periodLabel(result.period) + '): ' +
                plural(result.level_students, 'estudiante', 'estudiantes') + '.');
            state.openLevels.add(course.level);
            state.openCourses.add(course.id);
            return load().then(() => loadStudents(course));
        }).catch((error) => {
            setStatus(errorMessage(error), true);
            control.disabled = false;
        });
    }

    async function deleteCourse(course) {
        const ok = await confirmAction({
            title: '¿Eliminar este curso?',
            message: 'Se conserva con sus estudiantes y queda registrado quién lo eliminó. ' +
                'Solo el administrador puede habilitarlo de nuevo.',
            details: [
                ['Curso', course.name],
                ['Materia', course.competency_label],
                ['Nivel', 'Nivel ' + course.level],
                ['Estudiantes', formatNumber(course.students)]
            ],
            confirmLabel: 'Eliminar curso',
            tone: 'danger'
        });
        if (!ok) {
            return;
        }
        apiPost('course_delete', { course_id: course.id }, state.csrfToken).then(() => {
            state.openCourses.delete(course.id);
            state.students.delete(course.id);
            setStatus('Se eliminó el curso "' + course.name + '". El administrador puede habilitarlo desde "Cursos eliminados".');
            return load();
        }).catch((error) => setStatus(errorMessage(error), true));
    }

    async function removeStudent(course, student) {
        const ok = await confirmAction({
            title: '¿Quitar al estudiante del curso?',
            message: 'Deja de estar inscrito en este curso. Puedes volver a agregarlo con "Agregar estudiantes" si sigue teniendo el nivel.',
            details: [['Estudiante', student.name], ['Curso', course.name]],
            confirmLabel: 'Quitar del curso',
            tone: 'danger'
        });
        if (!ok) {
            return;
        }
        apiPost('course_remove_student', { course_id: course.id, student_id: student.student_id }, state.csrfToken).then(() => {
            setStatus('Se quitó a ' + student.name + ' de "' + course.name + '".');
            return load().then(() => loadStudents(course));
        }).catch((error) => setStatus(errorMessage(error), true));
    }

    elements.form.addEventListener('submit', (event) => {
        event.preventDefault();
        const payload = {
            name: elements.name.value.trim(),
            level: Number(elements.level.value),
            competency: elements.competency.value,
            description: elements.description.value.trim(),
            methodology: elements.methodology.value.trim()
        };
        if (payload.name.length < 3) {
            setStatus('Escribe un nombre de al menos 3 caracteres.', true);
            elements.name.focus();
            return;
        }
        if (payload.description.length < 10 || payload.methodology.length < 10) {
            setStatus('Escribe la descripción y la metodología (al menos 10 caracteres cada una).', true);
            (payload.description.length < 10 ? elements.description : elements.methodology).focus();
            return;
        }
        elements.submit.disabled = true;
        apiPost('course_create', payload, state.csrfToken).then((course) => {
            setStatus('Se creó "' + course.name + '" (' + course.competency_label + ', Nivel ' + course.level +
                '). Ahora puedes agregar sus estudiantes.');
            elements.name.value = '';
            elements.description.value = '';
            elements.methodology.value = '';
            state.openLevels.add(course.level);
            return load();
        }).catch((error) => {
            setStatus(errorMessage(error), true);
        }).finally(() => {
            elements.submit.disabled = false;
        });
    });

    elements.period.addEventListener('change', () => {
        state.period = elements.period.value;
    });

    elements.sections.forEach((section) => {
        section.querySelector('[data-course-level-toggle]').addEventListener('click', () => {
            const level = Number(section.dataset.courseLevelSection);
            if (state.openLevels.has(level)) {
                state.openLevels.delete(level);
            } else {
                state.openLevels.add(level);
            }
            render();
        });
    });

    root.querySelector('[data-courses-retry]').addEventListener('click', load);

    load();
}
