<?php
$dashboardLevel = $_GET['level'] ?? 'global';
$dashboardLevel = is_string($dashboardLevel) && in_array($dashboardLevel, ['global', 'program', 'student'], true)
    ? $dashboardLevel
    : 'global';
$dashboardImportId = $_GET['import_id'] ?? '';
$dashboardProgramId = $_GET['program_id'] ?? '';
$dashboardStudentRef = $_GET['student_ref'] ?? '';
$dashboardYear = $_GET['year'] ?? '';
$dashboardSimulation = $_GET['simulation'] ?? '';
$dashboardSubject = $_GET['subject'] ?? 'global';
$dashboardPage = $_GET['page'] ?? '1';
?>
<div class="dashboard-app"
     data-dashboard
     data-level="<?= h($dashboardLevel) ?>"
     data-import-id="<?= h($dashboardImportId) ?>"
     data-program-id="<?= h($dashboardProgramId) ?>"
     data-student-ref="<?= h($dashboardStudentRef) ?>"
     data-year="<?= h($dashboardYear) ?>"
     data-simulation="<?= h($dashboardSimulation) ?>"
     data-subject="<?= h($dashboardSubject) ?>"
     data-page="<?= h($dashboardPage) ?>"
     data-csrf-token="<?= h($csrfToken) ?>">
    <section class="dashboard-welcome">
        <div>
            <p class="eyebrow">TU ESPACIO DE TRABAJO</p>
            <h1>Hola, <?= h(explode(' ', trim((string) $usuarioNombre))[0] ?: $usuarioNombre) ?> <span class="welcome-spark">✦</span></h1>
            <p class="welcome-copy">Consulta el desempeño histórico de los programas y sus estudiantes.</p>
        </div>
        <div class="session-badge"><span></span>Sesión activa</div>
    </section>

    <section class="dashboard-status panel" data-dashboard-loading role="status">
        <span class="loading-spinner" aria-hidden="true"></span>
        <strong>Cargando resultados académicos…</strong>
        <p>Estamos consultando los datos guardados.</p>
    </section>

    <section class="dashboard-status panel dashboard-error" data-dashboard-error hidden role="alert">
        <span class="status-symbol">!</span>
        <strong data-error-title>No fue posible cargar el dashboard</strong>
        <p data-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
        <button type="button" class="button button-secondary" data-retry-dashboard>Reintentar</button>
    </section>

    <section class="dashboard-status panel dashboard-no-import" data-dashboard-no-import hidden>
        <span class="chart-icon" aria-hidden="true">▥</span>
        <h2>Aún no hay resultados importados</h2>
        <p>Sube una vez el libro que contiene las hojas <strong>BD GEN</strong> y <strong>TD PROGRAMAS</strong>. Después podrás consultar aquí los resultados guardados.</p>
        <a class="button button-primary" href="index.php?view=report">Importar primer Excel <span>→</span></a>
    </section>

    <div class="dashboard-content" data-dashboard-content hidden>
        <section class="dashboard-filters panel" aria-label="Filtros de resultados">
            <div class="filter-heading">
                <div><p class="eyebrow">CONSULTA HISTÓRICA</p><h2>Filtros</h2></div>
                <button type="button" class="filter-reset" data-reset-filters>Restablecer</button>
            </div>
            <div class="filter-controls">
                <label class="filter-field"><span>Año</span><select data-filter-year aria-label="Filtrar por año"><option value="">Todos</option></select></label>
                <label class="filter-field"><span>Asignatura</span><select data-filter-subject aria-label="Filtrar por asignatura"><option value="global">Global</option></select></label>
                <label class="filter-field"><span>Simulacro</span><select data-filter-simulation aria-label="Filtrar por simulacro"><option value="">Todos</option></select></label>
            </div>
            <div class="applied-context" data-filter-context></div>
        </section>

        <section class="dashboard-view" data-level-view="global" hidden>
            <div class="module-heading dashboard-title-row">
                <div><p class="eyebrow">RESULTADOS HISTÓRICOS</p><h2>TD PROGRAMAS</h2><p>Compara el desempeño global y por asignatura de los programas.</p></div>
                <label class="program-filter"><span>Programa</span><select data-program-filter aria-label="Seleccionar programa para analizar"><option value="">Todos los programas</option></select></label>
            </div>

            <div class="dashboard-kpis">
                <article class="kpi-card"><span class="kpi-icon">▥</span><div><span>Promedio global</span><strong data-kpi-average>—</strong><small>Según filtros activos</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">▤</span><div><span>Programas</span><strong data-kpi-programs>—</strong><small>En la consulta</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">♧</span><div><span>Estudiantes evaluados</span><strong data-kpi-students>—</strong><small>Identificados en los datos</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">✓</span><div><span>Presentaciones</span><strong data-kpi-presentations>—</strong><small>Intentos presentados</small></div></article>
            </div>

            <section class="panel selected-program-panel" data-selected-program-panel hidden>
                <div class="chart-card-heading">
                    <div><p class="eyebrow">ANÁLISIS DEL PROGRAMA</p><h3 data-selected-program-name></h3><p>Promedio global y resultados por asignatura con los filtros activos.</p></div>
                    <a class="button button-secondary" data-open-selected-program href="#">Abrir detalle <span>→</span></a>
                </div>
                <div class="selected-program-kpis"><span>Promedio global</span><strong data-selected-program-average>—</strong></div>
                <div class="chart-scroll"><svg class="dashboard-chart competency-chart" data-selected-program-chart role="img"></svg></div>
            </section>

            <div class="dashboard-chart-grid">
                <section class="panel chart-card bubble-card">
                    <div class="chart-card-heading"><div><p class="eyebrow">COMPARACIÓN</p><h3>Programas</h3><p>Selecciona un programa para consultar su detalle.</p></div><span class="chart-badge" data-program-page-label></span></div>
                    <div class="chart-scroll"><svg class="dashboard-chart bubble-chart" data-program-bubbles role="img"></svg></div>
                    <div class="empty-chart" data-empty-bubbles hidden>No hay programas con resultados para estos filtros.</div>
                    <div class="chart-pagination"><button type="button" class="button button-secondary" data-program-prev>Anterior</button><span data-program-pages></span><button type="button" class="button button-secondary" data-program-next>Siguiente</button></div>
                </section>
                <section class="panel chart-card comparison-card">
                    <div class="chart-card-heading"><div><p class="eyebrow">DESEMPEÑO</p><h3 data-comparison-title>Promedio global por programa</h3><p>Valores reportados por la API para la consulta activa.</p></div></div>
                    <div class="chart-scroll"><svg class="dashboard-chart comparison-chart" data-program-comparison role="img"></svg></div>
                    <div class="empty-chart" data-empty-comparison hidden>No hay calificaciones disponibles para el indicador seleccionado.</div>
                </section>
            </div>
        </section>

        <section class="dashboard-view" data-level-view="program" hidden>
            <div class="detail-heading">
                <a class="back-link" data-back-global href="index.php?view=dashboard"><span>←</span> Volver a TD PROGRAMAS</a>
                <p class="eyebrow">DETALLE DEL PROGRAMA</p>
                <h2 data-program-title></h2>
                <p>Desempeño, asignaturas y estudiantes para los filtros seleccionados.</p>
            </div>
            <div class="dashboard-kpis program-kpis">
                <article class="kpi-card"><span class="kpi-icon">▥</span><div><span>Promedio global</span><strong data-program-average>—</strong><small>Programa seleccionado</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">♧</span><div><span>Estudiantes evaluados</span><strong data-program-students-count>—</strong><small>Identificados en el periodo</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">✓</span><div><span>Presentaciones</span><strong data-program-presentations>—</strong><small>Intentos presentados</small></div></article>
            </div>
            <section class="panel chart-card program-subjects">
                <div class="chart-card-heading"><div><p class="eyebrow">RESULTADOS</p><h3>Desempeño por asignatura</h3><p>Promedios calculados por la API.</p></div></div>
                <div class="chart-scroll"><svg class="dashboard-chart competency-chart" data-program-competencies role="img"></svg></div>
                <div class="empty-chart" data-empty-program-competencies hidden>No hay resultados para las asignaturas y filtros seleccionados.</div>
            </section>
            <section class="panel students-panel">
                <div class="chart-card-heading"><div><p class="eyebrow">ESTUDIANTES</p><h3>Resultados por estudiante</h3><p>La búsqueda consulta por nombre o documento dentro de este programa.</p></div></div>
                <label class="search-box student-search"><span>⌕</span><input type="search" data-student-search autocomplete="off" placeholder="Buscar por nombre o número de documento"><span class="search-status" data-student-search-status></span></label>
                <div class="table-wrap">
                    <table class="student-results-table">
                        <thead><tr><th>ESTUDIANTE</th><th>DOCUMENTO</th><th>AÑO</th><th>SIMULACRO</th><th>GLOBAL</th><th>ESTADO</th><th></th></tr></thead>
                        <tbody data-program-students></tbody>
                    </table>
                </div>
                <div class="empty-chart" data-empty-students hidden>No hay estudiantes para los filtros o la búsqueda actual.</div>
                <div class="chart-pagination student-pagination"><button type="button" class="button button-secondary" data-student-prev>Anterior</button><span data-student-pages></span><button type="button" class="button button-secondary" data-student-next>Siguiente</button></div>
            </section>
        </section>

        <section class="dashboard-view" data-level-view="student" hidden>
            <div class="detail-heading">
                <a class="back-link" data-back-program href="#"><span>←</span> Volver al programa</a>
                <p class="eyebrow">HISTORIAL INDIVIDUAL</p>
                <h2 data-student-title></h2>
                <p><span data-student-document></span><span class="student-program-separator">·</span><span data-student-program></span></p>
            </div>
            <div class="dashboard-kpis student-kpis">
                <article class="kpi-card"><span class="kpi-icon">▥</span><div><span data-student-score-label>Puntaje global</span><strong data-student-score>—</strong><small>Último intento en el contexto seleccionado</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">▤</span><div><span>Simulacros en el historial</span><strong data-student-attempts>—</strong><small>Coincidentes con los filtros</small></div></article>
                <article class="kpi-card"><span class="kpi-icon">↗</span><div><span>Promedio del programa</span><strong data-student-program-average>—</strong><small>Comparación del mismo contexto</small></div></article>
            </div>
            <section class="panel chart-card student-history-card">
                <div class="chart-card-heading"><div><p class="eyebrow">EVOLUCIÓN</p><h3 data-student-chart-title>Desempeño global</h3><p>Valores de cada intento; no se promedian resultados de periodos distintos.</p></div></div>
                <div class="chart-scroll"><svg class="dashboard-chart student-history-chart" data-student-history role="img"></svg></div>
                <div class="empty-chart" data-empty-history hidden>No hay resultados para el estudiante en los filtros seleccionados.</div>
            </section>
            <section class="panel student-detail-panel">
                <div class="chart-card-heading"><div><p class="eyebrow">INTENTO MÁS RECIENTE</p><h3>Detalle del resultado</h3></div><span class="chart-badge" data-student-attempt-context></span></div>
                <div class="student-scores" data-student-scores></div>
            </section>
        </section>
    </div>
</div>
