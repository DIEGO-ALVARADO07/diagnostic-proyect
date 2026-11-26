// Tarjetas de programa: nombre, métrica elegida y clic para abrir el detalle.

import { formatNumber } from '../format.js';

/**
 * @param {HTMLElement} container  Donde van las tarjetas.
 * @param {HTMLElement} empty      Mensaje "sin programas".
 * @param {Array} programs         Programas de la página actual.
 * @param {{label: string, valueOf: Function, onOpen: Function}} options
 */
export function drawBubbles(container, empty, programs, options) {
    container.replaceChildren();
    if (!programs.length) {
        empty.hidden = false;
        return;
    }
    empty.hidden = true;
    programs.forEach((program) => {
        const metric = formatNumber(options.valueOf(program));

        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'program-card';
        card.setAttribute('aria-label', program.name + ', ' + options.label + ': ' + metric);

        const name = document.createElement('span');
        name.className = 'program-card-name';
        name.textContent = program.name;
        card.appendChild(name);

        const label = document.createElement('span');
        label.className = 'program-card-metric-label';
        label.textContent = options.label;
        card.appendChild(label);

        const value = document.createElement('strong');
        value.className = 'program-card-metric';
        value.textContent = metric;
        card.appendChild(value);

        card.addEventListener('click', () => {
            options.onOpen(program);
        });
        container.appendChild(card);
    });
}
