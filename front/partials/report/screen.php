<section class="module-heading">
    <div>
        <p class="eyebrow">LECTURA DE ARCHIVOS</p>
        <h1>Leer reporte de Excel</h1>
        <p>Sube un libro y selecciona la hoja que deseas consultar.</p>
    </div>
    <span class="file-limit">Máximo 30 MB</span>
</section>

<section class="panel module-panel report-panel">
    <div class="report-guidance">
        <span class="guidance-mark">i</span>
        <p><strong>Antes de subir el archivo:</strong> revisa que el nombre de la hoja esté escrito exactamente igual que en Excel, incluyendo espacios, tildes y mayúsculas. Si no coincide, te mostraremos las hojas disponibles.</p>
    </div>
    <form method="post" enctype="multipart/form-data" class="upload-form">
        <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
        <input type="hidden" name="action" value="upload_excel">
        <label class="field"><span>Archivo de Excel</span>
            <span class="file-input-wrap"><input type="file" name="file" accept=".xlsx,.xlsm,.xls,.ods" required><small>Formatos permitidos: .xlsx, .xlsm, .xls y .ods</small></span>
        </label>
        <label class="field"><span>Nombre exacto de la hoja</span><input type="text" name="sheet_name" required maxlength="255" placeholder="Ej. Resultados 2026"></label>
        <div class="upload-actions"><button class="button button-primary" type="submit"><span>↑</span> Subir y leer archivo</button></div>
    </form>

    <?php if ($resultadoExcel): ?>
        <?php
        $filasExcel = $resultadoExcel['data'] ?? [];
        $columnasExcel = $filasExcel && is_array($filasExcel[0]) ? array_keys($filasExcel[0]) : [];
        ?>
        <div class="result-summary">
            <div><span class="result-check">✓</span><span><strong>Archivo procesado</strong><small><?= h($resultadoExcel['filename'] ?? '') ?> · Hoja: <?= h($resultadoExcel['sheet_read'] ?? '') ?></small></span></div>
            <span class="count-pill"><?= h($resultadoExcel['total_rows'] ?? 0) ?> filas</span>
        </div>
        <?php if ($filasExcel && $columnasExcel): ?>
            <div class="table-wrap result-table">
                <table>
                    <thead><tr><?php foreach ($columnasExcel as $columna): ?><th><?= h($columna) ?></th><?php endforeach; ?></tr></thead>
                    <tbody>
                    <?php foreach ($filasExcel as $fila): ?>
                        <tr><?php foreach ($columnasExcel as $columna): ?><td><?= h(is_scalar($fila[$columna] ?? null) ? ($fila[$columna] ?? '') : json_encode($fila[$columna], JSON_UNESCAPED_UNICODE)) ?></td><?php endforeach; ?></tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
            <?php if (($resultadoExcel['total_rows'] ?? 0) > count($filasExcel)): ?><p class="table-footnote">Vista previa de las primeras <?= count($filasExcel) ?> filas.</p><?php endif; ?>
        <?php else: ?>
            <div class="empty-state compact-empty"><strong>La hoja no contiene filas para mostrar.</strong></div>
        <?php endif; ?>
    <?php endif; ?>
</section>

<?php if ($errorHoja): ?>
    <div class="modal-backdrop" data-sheet-modal role="dialog" aria-modal="true" aria-labelledby="sheet-error-title">
        <div class="modal-card">
            <button type="button" class="modal-close" data-close-modal aria-label="Cerrar">×</button>
            <div class="modal-warning">!</div>
            <p class="eyebrow">REVISIÓN DEL ARCHIVO</p>
            <h2 id="sheet-error-title">El nombre de la hoja no coincide</h2>
            <p class="modal-message"><?= h($errorHoja['message'] ?? 'Revisa el nombre de la hoja e inténtalo nuevamente.') ?></p>
            <div class="entered-sheet">Ingresaste: <strong><?= h($errorHoja['entered_name'] ?? '') ?></strong></div>
            <?php if (!empty($errorHoja['available_sheets'])): ?>
                <div class="available-sheets"><strong>Hojas disponibles en el archivo</strong><ul><?php foreach ($errorHoja['available_sheets'] as $hoja): ?><li><?= h($hoja) ?></li><?php endforeach; ?></ul></div>
            <?php endif; ?>
            <button type="button" class="button button-primary modal-action" data-close-modal>Entendido</button>
        </div>
    </div>
<?php endif; ?>
