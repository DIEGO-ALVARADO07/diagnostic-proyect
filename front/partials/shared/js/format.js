// Formato de números y textos. Funciones puras, sin DOM ni estado.

export function parsePositiveInteger(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function numberOrNull(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function formatNumber(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        return 'Sin datos';
    }
    return new Intl.NumberFormat('es-CO', {
        maximumFractionDigits: 2
    }).format(value);
}

export function truncate(value, limit) {
    const text = String(value || '');
    return text.length > limit ? text.slice(0, limit - 1) + '…' : text;
}
