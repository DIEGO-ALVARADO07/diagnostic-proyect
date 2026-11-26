/**
 * Ventana de confirmación propia de la aplicación (en lugar de window.confirm).
 *
 *   window.appConfirm({
 *       title: '¿Eliminar el curso?',
 *       message: 'Texto explicativo (admite saltos de línea).',
 *       details: [['Curso', 'Inglés básico'], ['Nivel', '1']],   // opcional
 *       confirmLabel: 'Eliminar', cancelLabel: 'Cancelar',
 *       tone: 'danger' | 'primary'
 *   }).then(function (ok) { ... });
 *
 * Esc o clic fuera cancelan. Al cerrar, el foco vuelve a donde estaba.
 */
window.appConfirm = function (options) {
    options = options || {};
    var tone = options.tone === 'primary' ? 'primary' : 'danger';
    return new Promise(function (resolve) {
        var previousFocus = document.activeElement;
        var overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';

        var dialog = document.createElement('div');
        dialog.className = 'confirm-dialog is-' + tone;
        dialog.setAttribute('role', 'alertdialog');
        dialog.setAttribute('aria-modal', 'true');
        var titleId = 'confirm-title-' + Date.now();
        dialog.setAttribute('aria-labelledby', titleId);

        var head = document.createElement('div');
        head.className = 'confirm-head';
        var icon = document.createElement('span');
        icon.className = 'confirm-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = options.icon || (tone === 'primary' ? '⟲' : '!');
        var copy = document.createElement('div');
        var title = document.createElement('h2');
        title.id = titleId;
        title.textContent = options.title || '¿Confirmas esta acción?';
        copy.appendChild(title);
        if (options.message) {
            var message = document.createElement('p');
            message.className = 'confirm-message';
            message.textContent = options.message;
            copy.appendChild(message);
        }
        head.append(icon, copy);
        dialog.appendChild(head);

        if (options.details && options.details.length) {
            var details = document.createElement('dl');
            details.className = 'confirm-details';
            options.details.forEach(function (pair) {
                var term = document.createElement('dt');
                term.textContent = pair[0];
                var value = document.createElement('dd');
                value.textContent = pair[1];
                details.append(term, value);
            });
            dialog.appendChild(details);
        }

        var actions = document.createElement('div');
        actions.className = 'confirm-actions';
        var cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'button button-secondary';
        cancel.textContent = options.cancelLabel || 'Cancelar';
        var accept = document.createElement('button');
        accept.type = 'button';
        accept.className = 'button ' + (tone === 'primary' ? 'button-primary' : 'button-danger');
        accept.textContent = options.confirmLabel || 'Confirmar';
        actions.append(cancel, accept);
        dialog.appendChild(actions);
        overlay.appendChild(dialog);

        function close(result) {
            document.removeEventListener('keydown', onKey, true);
            overlay.remove();
            document.body.classList.remove('has-confirm');
            if (previousFocus && typeof previousFocus.focus === 'function') {
                previousFocus.focus();
            }
            resolve(result);
        }
        function onKey(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                close(false);
            } else if (event.key === 'Tab') {
                // Mantiene el foco dentro de la ventana.
                var first = cancel;
                var last = accept;
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }
        }
        cancel.addEventListener('click', function () { close(false); });
        accept.addEventListener('click', function () { close(true); });
        overlay.addEventListener('click', function (event) {
            if (event.target === overlay) {
                close(false);
            }
        });
        document.addEventListener('keydown', onKey, true);

        document.body.appendChild(overlay);
        document.body.classList.add('has-confirm');
        // En acciones de riesgo, el foco empieza en "Cancelar".
        (tone === 'danger' ? cancel : accept).focus();
    });
};

document.addEventListener('DOMContentLoaded', function () {
    var search = document.querySelector('[data-table-search]');
    var roleFilter = document.querySelector('[data-role-filter]');
    var rows = Array.prototype.slice.call(document.querySelectorAll('[data-user-row]'));

    function filterRows() {
        var query = search ? search.value.trim().toLocaleLowerCase() : '';
        var role = roleFilter ? roleFilter.value : '';
        rows.forEach(function (row) {
            var matchesText = (row.dataset.search || '').toLocaleLowerCase().includes(query);
            var matchesRole = !role || row.dataset.role === role;
            row.hidden = !matchesText || !matchesRole;
        });
    }

    if (search) {
        search.addEventListener('input', filterRows);
    }
    if (roleFilter) {
        roleFilter.addEventListener('change', filterRows);
    }

    // Formularios con data-confirm (desactivar cuentas, desactivar o restaurar
    // importaciones): piden confirmación con la ventana propia antes de enviarse.
    // Opcionales: data-confirm-title, data-confirm-label, data-confirm-tone="primary".
    document.querySelectorAll('[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (form.dataset.confirmed === '1') {
                return;
            }
            event.preventDefault();
            window.appConfirm({
                title: form.dataset.confirmTitle,
                message: form.dataset.confirm,
                confirmLabel: form.dataset.confirmLabel,
                tone: form.dataset.confirmTone
            }).then(function (ok) {
                if (ok) {
                    form.dataset.confirmed = '1';
                    form.submit();
                }
            });
        });
    });

    var sidebar = document.querySelector('.sidebar');
    var menuToggle = document.querySelector('[data-menu-toggle]');
    if (sidebar && menuToggle) {
        menuToggle.addEventListener('click', function () {
            sidebar.classList.toggle('is-open');
        });
        sidebar.querySelectorAll('.nav-link').forEach(function (link) {
            link.addEventListener('click', function () {
                sidebar.classList.remove('is-open');
            });
        });
    }

    var modal = document.querySelector('[data-sheet-modal]');
    if (modal) {
        function closeModal() {
            modal.remove();
        }
        modal.querySelectorAll('[data-close-modal]').forEach(function (button) {
            button.addEventListener('click', closeModal);
        });
        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && document.body.contains(modal)) {
                closeModal();
            }
        });
        var closeButton = modal.querySelector('[data-close-modal]');
        if (closeButton) {
            closeButton.focus();
        }
    }

    document.querySelectorAll('.upload-form').forEach(function (form) {
        form.addEventListener('submit', function () {
            var button = form.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
                button.textContent = 'Procesando archivo...';
            }
        });
    });
});
