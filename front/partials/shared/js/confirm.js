// Confirmación con la ventana propia de la aplicación (window.appConfirm, en
// dashboard.js). Si por algún motivo no está cargada, usa window.confirm.

/**
 * @param {{title: string, message?: string, details?: Array<[string, string]>,
 *          confirmLabel?: string, cancelLabel?: string, tone?: 'danger'|'primary'}} options
 * @returns {Promise<boolean>}
 */
export function confirmAction(options) {
    if (typeof window.appConfirm === 'function') {
        return window.appConfirm(options);
    }
    const text = [options.title, options.message].filter(Boolean).join('\n\n');
    return Promise.resolve(window.confirm(text));
}
