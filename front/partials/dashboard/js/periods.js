// Periodos "AAAA-S" (S = 1 o 2): separar año y periodo del año para los filtros.

export function splitPeriod(period) {
    const match = /^(\d{4})-([12])$/.exec(period || '');
    return match ? { year: match[1], semester: match[2] } : null;
}

/** Años con datos, del más reciente al más antiguo. */
export function yearsOf(periods) {
    const years = new Set();
    periods.forEach((period) => {
        const parts = splitPeriod(period);
        if (parts) {
            years.add(parts.year);
        }
    });
    return Array.from(years).sort().reverse();
}

/** Periodos del año (1 y/o 2) que tienen datos, el más reciente primero. */
export function semestersOf(periods, year) {
    return periods
        .map(splitPeriod)
        .filter((parts) => parts && parts.year === year)
        .map((parts) => parts.semester)
        .sort()
        .reverse();
}
