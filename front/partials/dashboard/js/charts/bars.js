// Barras horizontales: una fila por entrada { label, value }.

import { formatNumber, numberOrNull, truncate } from '../format.js';
import { chartElement, chartText, prepareSvg } from './svg.js';

export function drawBars(svg, entries, title, description, emptyElement) {
    const validEntries = entries.filter((entry) => numberOrNull(entry.value) !== null);
    if (!validEntries.length) {
        svg.replaceChildren();
        if (emptyElement) {
            emptyElement.hidden = false;
        }
        return;
    }
    if (emptyElement) {
        emptyElement.hidden = true;
    }

    const width = 900;
    const rowHeight = 39;
    const top = 26;
    const height = top + validEntries.length * rowHeight + 16;
    const labelWidth = validEntries.length > 10 ? 190 : 220;
    const barWidth = width - labelWidth - 80;
    let maxValue = Math.max.apply(null, validEntries.map((item) => item.value));
    if (maxValue <= 0) {
        maxValue = 1;
    }
    prepareSvg(svg, title, description, '0 0 ' + width + ' ' + height);

    [0, 0.25, 0.5, 0.75, 1].forEach((fraction) => {
        const x = labelWidth + fraction * barWidth;
        chartElement(svg, 'line', {
            x1: x,
            y1: 17,
            x2: x,
            y2: height - 11,
            class: 'chart-grid-line'
        });
        chartText(svg, formatNumber(maxValue * fraction), x, 12, 'chart-axis-label');
    });

    validEntries.forEach((entry, index) => {
        const y = top + index * rowHeight;
        chartText(svg, truncate(entry.label, 31), labelWidth - 12, y + 15, 'chart-row-label');
        chartElement(svg, 'rect', {
            x: labelWidth,
            y: y + 3,
            width: Math.max(2, barWidth * entry.value / maxValue),
            height: 18,
            rx: 4,
            class: 'chart-bar'
        });
        chartText(svg, formatNumber(entry.value), labelWidth + barWidth * entry.value / maxValue + 8, y + 17, 'chart-value-label');
    });
}
