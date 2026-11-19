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

    document.querySelectorAll('[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
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
