<?php
// Módulo Estudiantes (fase 13a): todos los estudiantes de los Excel por nivel.
// No son cuentas de usuario: salen de las cargas de ESE y CORHUILA.
$gruposNivel = [
    ['key' => '1', 'title' => 'Nivel 1', 'hint' => 'Competencias de 0 a 125'],
    ['key' => '2', 'title' => 'Nivel 2', 'hint' => 'Competencias de 126 a 156'],
    ['key' => '3', 'title' => 'Nivel 3', 'hint' => 'Competencias de 157 a 198'],
    ['key' => '4', 'title' => 'Nivel 4', 'hint' => 'Competencias de 199 a 300'],
    ['key' => 'sin-resultado', 'title' => 'Sin resultado', 'hint' => 'Nunca presentaron'],
];
?>
<div class="dashboard-app students-app"
     data-students
     data-period="<?= h($_GET['period'] ?? '') ?>"
     data-level="<?= h($_GET['level'] ?? '') ?>"
     data-program-id="<?= h($_GET['program_id'] ?? '') ?>"
     data-search="<?= h($_GET['search'] ?? '') ?>">
    <section class="module-heading">
        <div>
            <p class="eyebrow">SEGUIMIENTO ACADÉMICO</p>
            <h1>Estudiantes</h1>
            <p>Estudiantes de los Excel de ESE y CORHUILA, agrupados por nivel. Arranca en el periodo actual; elige otro año o el histórico completo.</p>
        </div>
        <span class="count-pill" data-students-total>— estudiantes</span>
    </section>

    <section class="panel dashboard-filters students-filters" aria-label="Periodo de los estudiantes">
        <div class="filter-heading">
            <div><p class="eyebrow">FILTROS</p><h2>Periodo</h2></div>
            <button type="button" class="filter-reset" data-students-reset>Volver al último periodo</button>
        </div>
        <div class="filter-controls students-filter-controls">
            <label class="filter-field"><span>Año</span><select data-students-year aria-label="Filtrar por año"></select></label>
            <label class="filter-field"><span>Periodo</span><select data-students-semester aria-label="Filtrar por periodo del año"></select></label>
            <label class="filter-field"><span>Programa</span><select data-students-program aria-label="Filtrar por programa"><option value="">Todos los programas</option></select></label>
        </div>
    </section>

    <section class="level-groups" aria-label="Grupos por nivel">
        <?php foreach ($gruposNivel as $grupo): ?>
            <button type="button" class="level-group level-group-<?= h($grupo['key']) ?>" data-level-group="<?= h($grupo['key']) ?>" aria-pressed="false">
                <span class="level-group-title"><?= h($grupo['title']) ?></span>
                <strong data-level-count>—</strong>
                <small data-level-share>&nbsp;</small>
                <span class="level-group-hint"><?= h($grupo['hint']) ?></span>
            </button>
        <?php endforeach; ?>
    </section>

    <section class="panel module-panel students-panel">
        <div class="table-toolbar students-toolbar">
            <label class="search-box"><span>⌕</span><input type="search" data-students-search maxlength="120" placeholder="Buscar por nombre, documento o correo" aria-label="Buscar estudiante"></label>
        </div>
        <div class="students-context">
            <span data-students-context></span>
            <button type="button" class="filter-reset" data-students-clear hidden>Ver todos los niveles</button>
        </div>

        <div class="students-status" data-students-loading role="status">
            <span class="loading-spinner" aria-hidden="true"></span>
            <strong>Cargando estudiantes…</strong>
        </div>
        <div class="students-status dashboard-error" data-students-error hidden role="alert">
            <span class="status-symbol">!</span>
            <strong>No fue posible cargar los estudiantes</strong>
            <p data-students-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
            <button type="button" class="button button-secondary" data-students-retry>Reintentar</button>
        </div>
        <div class="empty-state" data-students-empty hidden>
            <span>♧</span>
            <strong data-students-empty-title>No hay estudiantes para mostrar</strong>
            <p data-students-empty-copy>Los estudiantes aparecen aquí al importar los Excel de ESE o de CORHUILA.</p>
        </div>

        <div data-students-content hidden>
            <div class="table-wrap">
                <table class="students-table">
                    <thead>
                        <tr>
                            <th>ESTUDIANTE</th>
                            <th>DOCUMENTO</th>
                            <th>PROGRAMA</th>
                            <th>NIVEL</th>
                            <th title="Lectura crítica">LECTURA</th>
                            <th title="Competencias ciudadanas">CIUDADANAS</th>
                            <th title="Razonamiento cuantitativo">CUANTITATIVO</th>
                            <th>INGLÉS</th>
                            <th>PROMEDIO</th>
                            <th title="Periodo y prueba de los que sale el nivel">SEGÚN</th>
                        </tr>
                    </thead>
                    <tbody data-students-rows></tbody>
                </table>
            </div>
            <div class="chart-pagination student-pagination" data-students-pagination>
                <button type="button" class="button button-secondary" data-students-prev>← Anterior</button>
                <span data-students-page></span>
                <button type="button" class="button button-secondary" data-students-next>Siguiente →</button>
            </div>
        </div>
        <p class="dashboard-note" data-students-rule></p>
    </section>
</div>
