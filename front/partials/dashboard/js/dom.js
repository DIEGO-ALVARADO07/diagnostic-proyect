// Ayudas de pantalla: textos, estados de carga, selects y celdas.

export function setText(root, selector, value) {
    const element = root.querySelector(selector);
    if (element) {
        element.textContent = value === null || value === undefined ? '' : String(value);
    }
}

/** Muestra uno de los estados: 'loading', 'error', 'empty' o 'content'. */
export function showState(elements, name) {
    elements.loading.hidden = name !== 'loading';
    elements.errorBox.hidden = name !== 'error';
    elements.noImport.hidden = name !== 'empty';
    elements.content.hidden = name !== 'content';
}

export function addOption(select, value, label) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
}

/**
 * Llena un select. Si `allLabel` no es null, agrega primero la opción vacía.
 * Devuelve si el valor `selected` existe entre las opciones.
 */
export function populateSelect(select, options, selected, allLabel) {
    select.replaceChildren();
    if (allLabel !== null) {
        addOption(select, '', allLabel);
    }
    options.forEach((option) => {
        addOption(select, String(option.value), option.label);
    });
    const available = Array.prototype.some.call(select.options, (option) => option.value === selected);
    if (available) {
        select.value = selected;
    } else if (allLabel === null) {
        select.value = select.options[0] ? select.options[0].value : '';
    } else {
        select.value = '';
    }
    return available;
}

export function addCell(row, value, className) {
    const cell = document.createElement('td');
    if (className) {
        cell.className = className;
    }
    cell.textContent = value === null || value === undefined ? '—' : String(value);
    row.appendChild(cell);
}
