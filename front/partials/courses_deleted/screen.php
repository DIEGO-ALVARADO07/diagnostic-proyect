<?php
// Panel del administrador: cursos eliminados (lógicamente) con toda su
// información y el botón Habilitar. Lo llena js/main.js con GET /courses/deleted.
?>
<div class="dashboard-app courses-app courses-deleted-app"
     data-courses-deleted
     data-csrf-token="<?= h($csrfToken) ?>">
    <section class="module-heading">
        <div>
            <p class="eyebrow">ADMINISTRACIÓN · AUDITORÍA</p>
            <h1>Cursos eliminados</h1>
            <p>La eliminación es lógica: cada curso conserva su información y sus estudiantes. Al habilitarlo vuelve a su nivel tal como estaba y queda registrado quién lo hizo.</p>
        </div>
        <span class="count-pill" data-deleted-total>— cursos</span>
    </section>

    <section class="panel module-panel">
        <p class="courses-status" data-deleted-status role="status" aria-live="polite"></p>

        <div class="students-status" data-deleted-loading role="status">
            <span class="loading-spinner" aria-hidden="true"></span>
            <strong>Cargando cursos eliminados…</strong>
        </div>
        <div class="students-status dashboard-error" data-deleted-error hidden role="alert">
            <span class="status-symbol">!</span>
            <strong>No fue posible cargar los cursos eliminados</strong>
            <p data-deleted-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
            <button type="button" class="button button-secondary" data-deleted-retry>Reintentar</button>
        </div>
        <div class="empty-state" data-deleted-empty hidden>
            <span>✓</span>
            <strong>No hay cursos eliminados</strong>
            <p>Cuando un instructor o administrador elimine un curso, aparecerá aquí para revisarlo o habilitarlo.</p>
        </div>

        <div class="table-wrap" data-deleted-content hidden>
            <table class="deleted-courses-table">
                <thead>
                    <tr>
                        <th>CURSO</th>
                        <th>NIVEL</th>
                        <th>DESCRIPCIÓN</th>
                        <th>METODOLOGÍA</th>
                        <th>ESTUDIANTES</th>
                        <th>CREADO</th>
                        <th>ELIMINADO</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody data-deleted-rows></tbody>
            </table>
        </div>
    </section>
</div>
