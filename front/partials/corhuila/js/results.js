// Tabla "Resultados por estudiante" del módulo CORHUILA (fase 15).

import { addCell } from '../../shared/js/dom.js';
import { formatNumber } from '../../shared/js/format.js';

const COMPETENCIES = ['lectura_critica', 'competencias_ciudadanas', 'razonamiento_cuantitativo', 'ingles'];
const SIN_PROGRAMA_ID = 'sin-programa';

function levelBadge(level) {
    const badge = document.createElement('span');
    const key = level === null || level === undefined ? 'sin-resultado' : String(level);
    badge.className = 'level-badge level-badge-' + key;
    badge.textContent = key === 'sin-resultado' ? 'Sin resultado' : 'N' + key;
    return badge;
}

function semesterText(semester) {
    if (!semester) {
        return '—';
    }
    const number = semester.match(/\d+/);
    return number ? number[0] : semester;
}

/**
 * @param {HTMLElement} tbody
 * @param {Array} students  `students` de /excel/dashboard/{import_id}/results.
 */
export function renderResults(tbody, students) {
    tbody.replaceChildren();
    students.forEach((student) => {
        const row = document.createElement('tr');

        const person = document.createElement('td');
        person.className = 'students-person';
        const name = document.createElement('strong');
        name.textContent = student.name || 'Nombre no disponible';
        const email = document.createElement('small');
        email.textContent = student.email || 'Sin correo';
        person.append(name, email);
        row.appendChild(person);

        addCell(row, student.document
            ? (student.document_type ? student.document_type + ' ' : '') + student.document
            : 'Sin documento');
        addCell(row, student.program, student.program_id === SIN_PROGRAMA_ID ? 'is-sin-programa' : '');
        addCell(row, semesterText(student.semester), 'students-competency');

        const levelCell = document.createElement('td');
        levelCell.appendChild(levelBadge(student.level));
        row.appendChild(levelCell);

        COMPETENCIES.forEach((key) => {
            const score = student.scores ? student.scores[key] : null;
            addCell(row, score === null || score === undefined ? '—' : formatNumber(score), 'students-competency');
        });
        addCell(row, student.average === null ? '—' : formatNumber(student.average), 'students-competency');
        tbody.appendChild(row);
    });
}
