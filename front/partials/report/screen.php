<section class="module-heading">
    <div>
        <p class="eyebrow">LECTURA DE ARCHIVOS</p>
        <h1>Importar reporte de Excel</h1>
        <p>Guarda los resultados una vez para consultarlos en el dashboard.</p>
    </div>
    <span class="file-limit">Máximo 30 MB</span>
</section>

<section class="panel module-panel report-panel">
    <div class="report-guidance">
        <span class="guidance-mark">i</span>
        <p><strong>Revisa el libro antes de subirlo:</strong> debe contener las hojas <strong>BD GEN</strong> y <strong>TD PROGRAMAS</strong>, con sus encabezados y estructura originales. La API valida el formato y conserva una versión histórica de cada importación.</p>
    </div>
    <form method="post" enctype="multipart/form-data" class="upload-form">
        <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
        <input type="hidden" name="action" value="upload_excel">
        <label class="field"><span>Archivo de Excel</span>
            <span class="file-input-wrap"><input type="file" name="file" accept=".xlsx,.xlsm,.xls,.ods" required><small>Formatos permitidos: .xlsx, .xlsm, .xls y .ods</small></span>
        </label>
        <div class="upload-actions"><button class="button button-primary" type="submit"><span>↑</span> Importar resultados</button></div>
    </form>

    <div class="import-notes">
        <span>✓</span>
        <p><strong>Los resultados se consultan desde la base de datos.</strong> No tendrás que volver a subir el mismo archivo para revisar sus datos. Los puntajes y promedios se calculan en la API.</p>
    </div>
</section>
