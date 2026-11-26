<?php
// Módulo CORHUILA: resultados de un periodo y estudiantes "Sin programa" (fase 12b).
require __DIR__ . '/../shared/compare-side.php';
?>
<div class="dashboard-app corhuila-app"
     data-corhuila
     data-period="<?= h($_GET['period'] ?? '') ?>"
     data-csrf-token="<?= h($csrfToken) ?>"
     data-upload-periods="<?= h(json_encode(periodosDeCarga())) ?>">
    <section class="dashboard-welcome">
        <div>
            <p class="eyebrow">MÓDULO CORHUILA</p>
            <h1>Prueba CORHUILA <span class="welcome-spark">✦</span></h1>
            <p class="welcome-copy">Resultados por periodo y estudiantes que quedaron sin programa.</p>
        </div>
        <a class="button button-primary" href="index.php?view=report&amp;source=CORHUILA"><span>↑</span> Subir Excel de CORHUILA</a>
    </section>

    <section class="panel dashboard-filters" aria-label="Filtros de CORHUILA">
        <div class="filter-heading">
            <div><p class="eyebrow">FILTROS</p><h2>Periodo</h2></div>
        </div>
        <div class="filter-controls corhuila-filter-controls">
            <label class="filter-field"><span>Periodo con archivo de CORHUILA</span><select data-corhuila-period aria-label="Elegir periodo de CORHUILA"></select></label>
        </div>
    </section>

    <section class="dashboard-status panel" data-corhuila-loading role="status">
        <span class="loading-spinner" aria-hidden="true"></span>
        <strong>Cargando CORHUILA…</strong>
        <p>Estamos consultando los resultados guardados.</p>
    </section>

    <section class="dashboard-status panel dashboard-error" data-corhuila-error hidden role="alert">
        <span class="status-symbol">!</span>
        <strong>No fue posible cargar CORHUILA</strong>
        <p data-corhuila-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
        <button type="button" class="button button-secondary" data-corhuila-retry>Reintentar</button>
    </section>

    <section class="dashboard-status panel dashboard-no-import" data-corhuila-empty hidden>
        <span class="chart-icon" aria-hidden="true">◧</span>
        <h2>Aún no hay archivos de CORHUILA</h2>
        <p>Sube el Excel de CORHUILA (hoja <strong>Calificaciones</strong> de Moodle) del periodo.</p>
        <a class="button button-primary" href="index.php?view=report&amp;source=CORHUILA">Subir Excel de CORHUILA <span>→</span></a>
    </section>

    <div class="dashboard-content" data-corhuila-content hidden>
        <?php renderCompareSide('corhuila', 'CORHUILA', ''); ?>

        <section class="panel without-program-panel" aria-label="Estudiantes sin programa">
            <div class="chart-card-heading">
                <div>
                    <p class="eyebrow">POR REVISAR</p>
                    <h3>Sin programa <span class="chart-badge" data-without-total></span></h3>
                    <p>Estudiantes de CORHUILA que no se encontraron en el histórico de ESE (ni por documento, ni por nombre completo, ni por correo). Asígnales el programa a mano: la asignación manual manda sobre ESE.</p>
                </div>
                <button type="button" class="button button-secondary" data-resolve>Recalcular cruce</button>
            </div>
            <p class="without-program-status" data-without-status role="status" aria-live="polite"></p>
            <div class="table-wrap">
                <table class="without-program-table">
                    <thead><tr><th>ESTUDIANTE</th><th>CORREO</th><th>DOCUMENTO</th><th>PROGRAMA</th><th></th></tr></thead>
                    <tbody data-without-rows></tbody>
                </table>
            </div>
            <div class="empty-chart" data-without-empty hidden>Todos los estudiantes de este periodo tienen programa.</div>
        </section>
    </div>
</div>
