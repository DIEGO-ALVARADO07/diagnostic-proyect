<?php
// Módulo CORHUILA: resultados de un periodo con filtros, detalle por programa,
// tabla de estudiantes y estudiantes "Sin programa" (fases 12b y 15).
require __DIR__ . '/../shared/compare-side.php';
?>
<div class="dashboard-app corhuila-app"
     data-corhuila
     data-period="<?= h($_GET['period'] ?? '') ?>"
     data-program-id="<?= h($_GET['program_id'] ?? '') ?>"
     data-semester="<?= h($_GET['semester'] ?? '') ?>"
     data-search="<?= h($_GET['search'] ?? '') ?>"
     data-page="<?= h($_GET['page'] ?? '1') ?>"
     data-csrf-token="<?= h($csrfToken) ?>"
     data-upload-periods="<?= h(json_encode(periodosDeCarga())) ?>">
    <section class="dashboard-welcome">
        <div>
            <p class="eyebrow">MÓDULO CORHUILA</p>
            <h1>Prueba CORHUILA <span class="welcome-spark">✦</span></h1>
            <p class="welcome-copy">Resultados por periodo y programa, búsqueda de estudiantes y estudiantes que quedaron sin programa.</p>
        </div>
        <a class="button button-primary" href="index.php?view=report&amp;source=CORHUILA"><span>↑</span> Subir Excel de CORHUILA</a>
    </section>

    <section class="panel dashboard-filters" aria-label="Filtros de CORHUILA">
        <div class="filter-heading">
            <div><p class="eyebrow">FILTROS</p><h2>Periodo, programa y estudiante</h2></div>
            <button type="button" class="filter-reset" data-corhuila-reset>Restablecer</button>
        </div>
        <div class="filter-controls corhuila-filter-controls">
            <label class="filter-field"><span>Periodo con archivo de CORHUILA</span><select data-corhuila-period aria-label="Elegir periodo de CORHUILA"></select></label>
            <label class="filter-field"><span>Programa</span><select data-corhuila-program aria-label="Filtrar por programa"><option value="">Todos los programas</option></select></label>
            <label class="filter-field"><span>Semestre</span><select data-corhuila-semester aria-label="Filtrar por semestre"><option value="">Todos los semestres</option></select></label>
            <label class="filter-field corhuila-search-field"><span>Buscar estudiante</span>
                <span class="search-box"><span aria-hidden="true">⌕</span><input type="search" data-corhuila-search maxlength="120" autocomplete="off" placeholder="Nombre, documento, correo o programa" aria-label="Buscar por nombre, documento, correo o programa"></span>
            </label>
        </div>
        <div class="applied-context" data-corhuila-context></div>
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
        <div class="detail-heading corhuila-program-heading" data-program-heading hidden>
            <button type="button" class="back-link text-button" data-back-all><span>←</span> Todos los programas</button>
            <p class="eyebrow">DETALLE DEL PROGRAMA</p>
            <h2 data-program-title></h2>
            <p>Promedio, competencias y estudiantes del programa en el periodo elegido.</p>
        </div>

        <?php renderCompareSide('corhuila', 'CORHUILA', ''); ?>

        <section class="panel students-panel corhuila-students-panel" aria-label="Estudiantes de CORHUILA">
            <div class="chart-card-heading">
                <div>
                    <p class="eyebrow">ESTUDIANTES</p>
                    <h3>Resultados por estudiante <span class="chart-badge" data-results-total></span></h3>
                    <p data-results-copy>Todos los estudiantes del periodo. Quien está en dos programas aparece una vez por programa.</p>
                </div>
            </div>
            <p class="without-program-status" data-results-status role="status" aria-live="polite"></p>
            <div class="table-wrap">
                <table class="students-table corhuila-results-table">
                    <thead>
                        <tr>
                            <th>ESTUDIANTE</th>
                            <th>DOCUMENTO</th>
                            <th>PROGRAMA</th>
                            <th>SEMESTRE</th>
                            <th>NIVEL</th>
                            <th title="Lectura crítica">LECTURA</th>
                            <th title="Competencias ciudadanas">CIUDADANAS</th>
                            <th title="Razonamiento cuantitativo">CUANTITATIVO</th>
                            <th>INGLÉS</th>
                            <th title="Promedio de las 4 competencias">PROMEDIO</th>
                        </tr>
                    </thead>
                    <tbody data-results-rows></tbody>
                </table>
            </div>
            <div class="empty-chart" data-results-empty hidden>No hay estudiantes para estos filtros o esta búsqueda.</div>
            <div class="chart-pagination student-pagination" data-results-pagination>
                <button type="button" class="button button-secondary" data-results-prev>← Anterior</button>
                <span data-results-page></span>
                <button type="button" class="button button-secondary" data-results-next>Siguiente →</button>
            </div>
        </section>

        <section class="panel without-program-panel" data-without-panel aria-label="Estudiantes sin programa">
            <div class="chart-card-heading">
                <div>
                    <p class="eyebrow">POR REVISAR</p>
                    <h3>Sin programa <span class="chart-badge" data-without-total></span></h3>
                    <p>Estudiantes de CORHUILA que no se encontraron en <strong>matriculados</strong> del periodo (por documento, o por nombre completo y uno de sus correos) ni en el histórico de ESE. Asígnales el programa a mano: la asignación manual manda sobre todo lo demás.</p>
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
