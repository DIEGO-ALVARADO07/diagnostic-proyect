// Peticiones al proxy PHP del dashboard y traducción de errores.

const ENDPOINT = 'partials/dashboard/data.php';

export function makeError(message, status, data) {
    const error = new Error(message);
    error.status = status;
    error.data = data;
    return error;
}

export function errorMessage(error) {
    const detail = error && error.data ? error.data.detail : null;
    if (typeof detail === 'string') {
        return detail;
    }
    if (detail && typeof detail.message === 'string') {
        return detail.message;
    }
    if (error && error.status === 403) {
        return 'Tu cuenta no tiene permiso para consultar estos resultados.';
    }
    if (error && error.status === 404) {
        return 'No hay una importación activa o la información solicitada ya no está disponible.';
    }
    return 'Verifica que la API esté disponible e inténtalo nuevamente.';
}

/** Llama al proxy; omite los parámetros vacíos y redirige al login si la sesión expiró. */
export function apiRequest(params, options) {
    // Relativa a la página (index.php), no a este archivo.
    const url = new URL(ENDPOINT, window.location.href);
    Object.keys(params || {}).forEach((key) => {
        const value = params[key];
        if (value !== '' && value !== null && value !== undefined) {
            url.searchParams.set(key, String(value));
        }
    });

    const requestOptions = Object.assign({
        headers: {
            Accept: 'application/json',
            'X-Dashboard-Request': '1'
        }
    }, options || {});

    return fetch(url.toString(), requestOptions).then((response) => response.json().catch(() => {
        throw makeError('La aplicación recibió una respuesta no válida.', response.status);
    }).then((data) => {
        if (response.status === 401) {
            window.location.assign('login.php');
            throw makeError('La sesión expiró.', 401, data);
        }
        if (!response.ok) {
            throw makeError(errorMessage({ status: response.status, data: data }), response.status, data);
        }
        return data;
    }));
}
