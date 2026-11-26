// Tabla "Sin programa": un select de programa y un botón Guardar por estudiante.

import { addCell, addOption } from '../../shared/js/dom.js';

/**
 * @param {HTMLElement} tbody
 * @param {Array} students   `students` de /review/without-program.
 * @param {Array} catalog    `programs` de /catalog/programs.
 * @param {(student: object, programId: number) => Promise} onSave
 */
export function renderWithoutProgram(tbody, students, catalog, onSave) {
    tbody.replaceChildren();
    students.forEach((student) => {
        const row = document.createElement('tr');
        addCell(row, student.name || 'Nombre no disponible');
        addCell(row, student.email || 'Sin correo');
        addCell(row, student.document || 'Sin documento');

        const selectCell = document.createElement('td');
        const select = document.createElement('select');
        select.setAttribute('aria-label', 'Programa de ' + (student.name || 'el estudiante'));
        addOption(select, '', 'Elige un programa');
        catalog.forEach((program) => addOption(select, program.program_id, program.name));
        selectCell.appendChild(select);
        row.appendChild(selectCell);

        const actionCell = document.createElement('td');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'button button-primary';
        button.textContent = 'Guardar';
        button.disabled = true;
        actionCell.appendChild(button);
        row.appendChild(actionCell);

        if (student.student_id === null || student.student_id === undefined) {
            // Sin registro de estudiante no hay a quién asignarle el programa.
            select.disabled = true;
            button.title = 'Esta fila no tiene estudiante asociado. Usa "Recalcular cruce".';
        } else {
            select.addEventListener('change', () => {
                button.disabled = select.value === '';
            });
            button.addEventListener('click', () => {
                button.disabled = true;
                select.disabled = true;
                button.textContent = 'Guardando…';
                onSave(student, Number(select.value)).catch(() => {
                    button.disabled = false;
                    select.disabled = false;
                    button.textContent = 'Guardar';
                });
            });
        }
        tbody.appendChild(row);
    });
}
