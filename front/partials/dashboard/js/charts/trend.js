// Línea de evolución de un estudiante: un punto por intento, sin promediar.

import { formatNumber, numberOrNull, truncate } from '../format.js';
import { chartElement, chartText, prepareSvg } from './svg.js';

export function drawStudentTrend(svg, entries, studentName, emptyElement) {
    const values = entries.filter((entry) => numberOrNull(entry.value) !== null);
    if (!values.length) {
        svg.replaceChildren();
        emptyElement.hidden = false;
        return;
    }
    emptyElement.hidden = true;
    const width = Math.max(720, values.length * 105);
    const height = 330;
    const left = 55;
    const right = 25;
    const top = 24;
    const bottom = 68;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const scores = values.map((entry) => entry.value);
    let minimum = Math.min.apply(null, scores);
    let maximum = Math.max.apply(null, scores);
    if (minimum === maximum) {
        minimum = minimum - 1;
        maximum = maximum + 1;
    }
    prepareSvg(
        svg,
        'Evolución del desempeño de ' + studentName,
        'Cada punto es un resultado individual. No se promedian intentos.',
        '0 0 ' + width + ' ' + height
    );

    for (let tick = 0; tick <= 4; tick += 1) {
        const fraction = tick / 4;
        const y = top + plotHeight * fraction;
        const score = maximum - (maximum - minimum) * fraction;
        chartElement(svg, 'line', {
            x1: left,
            y1: y,
            x2: width - right,
            y2: y,
            class: 'chart-grid-line'
        });
        chartText(svg, formatNumber(score), left - 9, y + 4, 'chart-axis-label');
    }

    const points = values.map((entry, index) => {
        const x = values.length === 1
            ? left + plotWidth / 2
            : left + plotWidth * index / (values.length - 1);
        const y = top + plotHeight * (maximum - entry.value) / (maximum - minimum);
        return { x: x, y: y, entry: entry };
    });
    chartElement(svg, 'polyline', {
        points: points.map((point) => point.x + ',' + point.y).join(' '),
        class: 'student-trend-line'
    });
    points.forEach((point) => {
        const circle = chartElement(svg, 'circle', {
            cx: point.x,
            cy: point.y,
            r: 5,
            class: 'student-trend-point'
        });
        const title = chartElement(svg, 'title', {}, circle);
        title.textContent = point.entry.label + ': ' + formatNumber(point.entry.value);
        chartText(svg, truncate(point.entry.label, 14), point.x, height - 31, 'chart-axis-label');
    });
}
