<?php
// Matriculados (fase 14a): archivo oficial de estudiantes de cada periodo.
// Solo el administrador lo sube y lo ve. Es la data principal: de aquí salen
// el programa y el semestre de los estudiantes de CORHUILA.
// La tabla la llena js/main.js con GET /enrollment/records.
$periodosCarga = periodosDeCarga();
$periodoPedido = $_GET['period'] ?? '';
$periodoCarga = in_array($periodoPedido, $periodosCarga, true) ? $periodoPedido : $periodosCarga[0];
?>
<div class="dashboard-app students-app enrollment-app"
     data-enrollment
     data-period="<?= h(is_string($periodoPedido) ? $periodoPedido : '') ?>"
     data-program="<?= h($_GET['program'] ?? '') ?>"
     data-semester="<?= h($_GET['semester'] ?? '') ?>"
     data-document-type="<?= h($_GET['document_type'] ?? '') ?>"
     data-gender="<?= h($_GET['gender'] ?? '') ?>"
     data-stratum="<?= h($_GET['stratum'] ?? '') ?>"
     data-search="<?= h($_GET['search'] ?? '') ?>">
    <section class="module-heading">
        <div>
            <p class="eyebrow">DATA PRINCIPAL · SOLO ADMINISTRADOR</p>
            <h1>Matriculados</h1>
            <p>Listado oficial de estudiantes de cada periodo. Súbelo <strong>antes</strong> que los resultados de CORHUILA: de aquí salen el programa y el semestre de cada estudiante. Un estudiante en dos programas aparece una vez por programa.</p>
        </div>
        <span class="count-pill" data-enrollment-total>— estudiantes</span>
    </section>

    <section class="panel module-panel report-panel enrollment-upload">
        <div class="report-guidance">
            <span class="guidance-mark">i</span>
            <p><strong>Archivo de matriculados del periodo</strong> (el de 2026-2, por ejemplo). Debe tener al menos las columnas <strong>PROGRAMA</strong>, <strong>IDENTIFICACION</strong>, <strong>NOMBRES</strong> y <strong>APELLIDOS</strong>; si trae <strong>COD_PERIODO</strong>, debe ser del periodo que elijas. Subir otro archivo del mismo periodo reemplaza al anterior.</p>
        </div>
        <form method="post" enctype="multipart/form-data" class="upload-form enrollment-upload-form">
            <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
            <input type="hidden" name="action" value="upload_enrollment">
            <label class="field"><span>Periodo</span>
                <select name="period" required>
                    <?php foreach ($periodosCarga as $indice => $periodo): ?>
                        <option value="<?= h($periodo) ?>"<?= $periodo === $periodoCarga ? ' selected' : '' ?>><?= h($periodo) ?><?= $indice === 0 ? ' (actual)' : ' (anterior)' ?></option>
                    <?php endforeach; ?>
                </select>
                <small class="field-hint">Periodo 1 (enero–junio) o 2 (julio–diciembre).</small>
            </label>
            <label class="field upload-file"><span>Archivo de matriculados</span>
                <span class="file-input-wrap"><input type="file" name="file" accept=".xlsx,.xlsm,.xls,.ods" required><small>Formatos permitidos: .xlsx, .xlsm, .xls y .ods (máximo 30 MB)</small></span>
            </label>
            <div class="upload-actions"><button class="button button-primary" type="submit"><span>↑</span> Subir matriculados</button></div>
        </form>

        <div class="enrollment-uploads" data-enrollment-uploads hidden>
            <p class="eyebrow">ARCHIVOS CARGADOS</p>
            <div class="enrollment-upload-cards" data-enrollment-upload-cards></div>
        </div>
    </section>

    <section class="panel dashboard-filters students-filters" aria-label="Filtros de matriculados" data-enrollment-filters hidden>
        <div class="filter-heading">
            <div><p class="eyebrow">FILTROS</p><h2>Matriculados del periodo</h2></div>
            <button type="button" class="filter-reset" data-enrollment-reset>Quitar filtros</button>
        </div>
        <div class="filter-controls enrollment-filter-controls">
            <label class="filter-field"><span>Periodo</span><select data-enrollment-period aria-label="Periodo"></select></label>
            <label class="filter-field"><span>Programa</span><select data-enrollment-program aria-label="Programa"></select></label>
            <label class="filter-field"><span>Semestre</span><select data-enrollment-semester aria-label="Semestre"></select></label>
            <label class="filter-field"><span>Tipo de documento</span><select data-enrollment-document-type aria-label="Tipo de documento"></select></label>
            <label class="filter-field"><span>Género</span><select data-enrollment-gender aria-label="Género"></select></label>
            <label class="filter-field"><span>Estrato</span><select data-enrollment-stratum aria-label="Estrato"></select></label>
        </div>
    </section>

    <section class="panel module-panel students-panel">
        <div class="table-toolbar students-toolbar">
            <label class="search-box"><span>⌕</span><input type="search" data-enrollment-search maxlength="120" placeholder="Buscar por nombre, documento, código o correo" aria-label="Buscar matriculado"></label>
        </div>
        <div class="students-context"><span data-enrollment-context></span></div>

        <div class="students-status" data-enrollment-loading role="status">
            <span class="loading-spinner" aria-hidden="true"></span>
            <strong>Cargando matriculados…</strong>
        </div>
        <div class="students-status dashboard-error" data-enrollment-error hidden role="alert">
            <span class="status-symbol">!</span>
            <strong>No fue posible cargar los matriculados</strong>
            <p data-enrollment-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
            <button type="button" class="button button-secondary" data-enrollment-retry>Reintentar</button>
        </div>
        <div class="empty-state" data-enrollment-empty hidden>
            <span>▦</span>
            <strong data-enrollment-empty-title>Todavía no hay matriculados</strong>
            <p data-enrollment-empty-copy>Sube el archivo de matriculados del periodo para empezar.</p>
        </div>

        <div data-enrollment-content hidden>
            <div class="table-wrap">
                <table class="students-table enrollment-table">
                    <thead>
                        <tr>
                            <th>ESTUDIANTE</th>
                            <th>DOCUMENTO</th>
                            <th>PROGRAMA</th>
                            <th>SEM.</th>
                            <th>CORREO INSTITUCIONAL</th>
                            <th>CORREO PERSONAL</th>
                            <th>TELÉFONO</th>
                            <th>MÓVIL</th>
                            <th>GÉNERO</th>
                            <th>ESTRATO</th>
                            <th>NACIMIENTO</th>
                        </tr>
                    </thead>
                    <tbody data-enrollment-rows></tbody>
                </table>
            </div>
            <div class="chart-pagination student-pagination" data-enrollment-pagination>
                <button type="button" class="button button-secondary" data-enrollment-prev>← Anterior</button>
                <span data-enrollment-page></span>
                <button type="button" class="button button-secondary" data-enrollment-next>Siguiente →</button>
            </div>
        </div>
    </section>
</div>
