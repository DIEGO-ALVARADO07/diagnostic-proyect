<?php
// Una mitad del comparativo (ESE o CORHUILA). La llena shared/js/compare-side.js.
// Uso: renderCompareSide('ese', 'ESE', 'ese'); con $module = '' no se muestra "Ver módulo".
if (!function_exists('renderCompareSide')) {
    function renderCompareSide(string $key, string $title, string $module): void { ?>
<section class="panel compare-side" data-side="<?= h($key) ?>" aria-label="Resultados de <?= h($title) ?>">
        <header class="compare-side-heading">
            <div>
                <p class="eyebrow"><?= h($title) ?></p>
                <h2 data-side-title><?= h($title) ?></h2>
                <p class="compare-side-file" data-side-file></p>
            </div>
            <?php if ($module !== ''): ?>
                <a class="button button-secondary compare-side-link" data-side-module href="index.php?view=<?= h($module) ?>">Ver módulo <span>→</span></a>
            <?php endif; ?>
        </header>

        <div class="compare-waiting" data-side-waiting hidden>
            <span class="compare-waiting-mark" aria-hidden="true">⏳</span>
            <strong>A la espera del archivo</strong>
            <p data-side-waiting-text></p>
            <a class="button button-primary" data-side-upload hidden href="#"><span>↑</span> Subir archivo de <?= h($title) ?></a>
        </div>

        <div class="compare-side-body" data-side-body hidden>
            <div class="compare-kpis">
                <article class="kpi-card"><span class="kpi-icon">▥</span><div><span>Promedio general</span><strong data-side-average>—</strong><small>4 competencias comunes</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">▤</span><div><span>Nivel promedio</span><strong data-side-level>—</strong><small>Escala N1 a N4</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">♧</span><div><span>Estudiantes evaluados</span><strong data-side-students>—</strong><small>Personas distintas</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">✓</span><div><span>Presentaciones</span><strong data-side-presentations>—</strong><small>Intentos presentados</small></div></article>
            </div>

            <div class="compare-block">
                <div class="chart-card-heading"><div><p class="eyebrow">COMPETENCIAS</p><h3>Promedio por competencia</h3></div><span class="chart-badge" data-side-weakest></span></div>
                <div class="chart-scroll"><svg class="dashboard-chart compare-chart" data-side-chart role="img"></svg></div>
                <div class="empty-chart" data-side-chart-empty hidden>No hay resultados por competencia con estos filtros.</div>
            </div>

            <div class="compare-block" data-side-programs-block>
                <div class="chart-card-heading"><div><p class="eyebrow">PROGRAMAS</p><h3>Promedio por programa</h3><p data-side-programs-hint>Del mejor al más bajo. "Sin programa" va al final.</p></div></div>
                <div class="table-wrap">
                    <table class="compare-programs-table">
                        <thead><tr><th>PROGRAMA</th><th>PROMEDIO</th><th>NIVEL</th><th>ESTUDIANTES</th></tr></thead>
                        <tbody data-side-programs></tbody>
                    </table>
                </div>
                <div class="empty-chart" data-side-programs-empty hidden>No hay programas con resultados para estos filtros.</div>
            </div>
        </div>
    </section>
<?php }
}
