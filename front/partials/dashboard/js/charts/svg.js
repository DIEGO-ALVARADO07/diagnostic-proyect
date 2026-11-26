// Primitivas SVG compartidas por las gráficas.

const SVG_NS = 'http://www.w3.org/2000/svg';

export function chartElement(svg, name, attributes, parent) {
    const element = document.createElementNS(SVG_NS, name);
    Object.keys(attributes || {}).forEach((key) => {
        element.setAttribute(key, attributes[key]);
    });
    (parent || svg).appendChild(element);
    return element;
}

export function chartText(svg, text, x, y, className, parent) {
    const node = chartElement(svg, 'text', {
        x: x,
        y: y,
        class: className || 'chart-label'
    }, parent);
    node.textContent = text;
    return node;
}

/** Limpia el SVG y le pone tamaño, título y descripción accesibles. */
export function prepareSvg(svg, title, description, viewBox) {
    svg.replaceChildren();
    svg.setAttribute('viewBox', viewBox);
    svg.setAttribute('preserveAspectRatio', 'xMinYMin meet');
    svg.setAttribute('aria-label', description);
    const titleNode = chartElement(svg, 'title', {});
    titleNode.textContent = title;
    const descriptionNode = chartElement(svg, 'desc', {});
    descriptionNode.textContent = description;
}
