<?php
// Dashboard principal: ESE frente a CORHUILA en un periodo (fase 12b).
require __DIR__ . '/../shared/compare-side.php';
?>
<div class="dashboard-app compare-app"
     data-compare
     data-period="<?= h($_GET['period'] ?? '') ?>"
     data-moment="<?= h($_GET['moment'] ?? '') ?>"
     data-program-id="<?= h($_GET['program_id'] ?? '') ?>"
     data-upload-periods="<?= h(json_encode(periodosDeCarga())) ?>">
    <section class="dashboard-welcome">
        <div>
            <p class="eyebrow">TU ESPACIO DE TRABAJO</p>
            <h1>Hola, <?= h(explode(' ', trim((string) $usuarioNombre))[0] ?: $usuarioNombre) ?> <span class="welcome-spark">✦</span></h1>
            <p class="welcome-copy">Compara ESE y CORHUILA en el mismo periodo.</p>
        </div>
        <div class="session-badge"><span></span>Sesión activa</div>
    </section>

    <section class="panel dashboard-filters" aria-label="Filtros del dashboard">
        <div class="filter-heading">
            <div><p class="eyebrow">FILTROS GLOBALES</p><h2>Periodo y programa</h2></div>
            <button type="button" class="filter-reset" data-compare-reset>Volver al último periodo</button>
        </div>
        <div class="filter-controls compare-filter-controls">
            <label class="filter-field"><span>Año</span><select data-compare-year aria-label="Filtrar por año"></select></label>
            <label class="filter-field"><span>Periodo</span><select data-compare-semester aria-label="Filtrar por periodo del año"></select></label>
            <label class="filter-field"><span>Momento (solo ESE)</span><select data-compare-moment aria-label="Filtrar ESE por momento"><option value="">Todos</option></select></label>
            <label class="filter-field"><span>Programa</span><select data-compare-program aria-label="Filtrar por programa"><option value="">Todos los programas</option></select></label>
        </div>
        <div class="applied-context" data-compare-context></div>
    </section>

    <section class="dashboard-status panel" data-compare-loading role="status">
        <span class="loading-spinner" aria-hidden="true"></span>
        <strong>Cargando el comparativo…</strong>
        <p>Estamos consultando ESE y CORHUILA.</p>
    </section>

    <section class="dashboard-status panel dashboard-error" data-compare-error hidden role="alert">
        <span class="status-symbol">!</span>
        <strong>No fue posible cargar el dashboard</strong>
        <p data-compare-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
        <button type="button" class="button button-secondary" data-compare-retry>Reintentar</button>
    </section>

    <section class="dashboard-status panel dashboard-no-import" data-compare-empty hidden>
        <span class="chart-icon" aria-hidden="true">▥</span>
        <h2>Aún no hay resultados importados</h2>
        <p>Sube el archivo de ESE o el de CORHUILA del periodo para ver aquí el comparativo.</p>
        <a class="button button-primary" href="index.php?view=report">Importar Excel <span>→</span></a>
    </section>

    <div class="dashboard-content" data-compare-content hidden>
        <div class="compare-columns">
            <?php renderCompareSide('ese', 'ESE', 'ese'); ?>
            <?php renderCompareSide('corhuila', 'CORHUILA', 'corhuila'); ?>
        </div>

        <section class="compare-highlights" aria-label="Hallazgos en común">
            <article class="panel compare-highlight" data-worst-program>
                <p class="eyebrow">PROGRAMA MÁS BAJO</p>
                <h3 data-worst-name>—</h3>
                <p class="compare-highlight-value"><span>Nivel promedio</span><strong data-worst-level>—</strong></p>
                <p class="compare-highlight-split"><span data-worst-ese></span><span data-worst-corhuila></span></p>
            </article>
            <article class="panel compare-highlight" data-lowest-competency>
                <p class="eyebrow">COMPETENCIA MÁS BAJA EN COMÚN</p>
                <h3 data-lowest-name>—</h3>
                <p class="compare-highlight-value"><span>Promedio</span><strong data-lowest-average>—</strong></p>
                <p class="compare-highlight-split"><span data-lowest-ese></span><span data-lowest-corhuila></span></p>
            </article>
        </section>
        <p class="dashboard-note" data-compare-note></p>
    </div>
</div>
