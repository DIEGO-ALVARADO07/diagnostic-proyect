<section class="module-heading imports-heading">
    <div>
        <p class="eyebrow">ADMINISTRACIÓN DE DATOS</p>
        <h1>Historial de Excel</h1>
        <p>Consulta todas las importaciones y desactiva los snapshots que ya no deban estar disponibles.</p>
    </div>
    <span class="count-pill"><?= h(count($importaciones)) ?> registros</span>
</section>

<section class="panel module-panel imports-panel">
    <div class="imports-notice">
        <span aria-hidden="true">i</span>
        <p>La desactivación es lógica: el registro se conserva con estado <strong>Desactivada</strong> para el superadmin, pero deja de aparecer en las consultas del resto de usuarios. Si desactivas el snapshot activo, el dashboard quedará sin datos hasta una nueva importación.</p>
    </div>

    <?php if ($errorImportaciones): ?>
        <div class="notice notice-error" role="alert"><?= h($errorImportaciones) ?></div>
    <?php elseif (!$importaciones): ?>
        <p class="imports-empty">Todavía no hay importaciones registradas.</p>
    <?php else: ?>
        <div class="table-wrap">
            <table class="imports-table">
                <thead>
                    <tr>
                        <th>ARCHIVO</th>
                        <th>FECHA DE CARGA</th>
                        <th>ESTADO</th>
                        <th>FILAS BD GEN</th>
                        <th>FILAS TD PROGRAMAS</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($importaciones as $importacion): ?>
                        <?php
                        $estadoImportacion = (string) ($importacion['status'] ?? '');
                        $importId = $importacion['import_id'] ?? '';
                        $puedeDesactivar = in_array($estadoImportacion, ['ACTIVE', 'HISTORICAL', 'FAILED'], true)
                            && is_string($importId)
                            && $importId !== '';
                        $etiquetasEstado = [
                            'ACTIVE' => 'Activa',
                            'HISTORICAL' => 'Histórica',
                            'FAILED' => 'Fallida',
                            'PROCESSING' => 'Procesando',
                            'VALIDATED' => 'Validada',
                            'DELETED' => 'Desactivada',
                        ];
                        ?>
                        <tr>
                            <td class="imports-filename"><?= h($importacion['filename'] ?? 'Archivo sin nombre') ?></td>
                            <td><?= h($importacion['imported_at'] ?? '—') ?></td>
                            <td>
                                <span class="imports-status imports-status-<?= h(strtolower($estadoImportacion)) ?>"><?= h($etiquetasEstado[$estadoImportacion] ?? $estadoImportacion) ?></span>
                                <?php if ($estadoImportacion === 'DELETED' && !empty($importacion['deleted_at'])): ?>
                                    <small class="imports-deleted-date">Desactivada: <?= h($importacion['deleted_at']) ?></small>
                                <?php endif; ?>
                            </td>
                            <td><?= h(number_format((int) ($importacion['bd_gen_row_count'] ?? 0), 0, ',', '.')) ?></td>
                            <td><?= h(number_format((int) ($importacion['td_programas_row_count'] ?? 0), 0, ',', '.')) ?></td>
                            <td class="imports-actions">
                                <?php if ($puedeDesactivar): ?>
                                    <form method="post" data-confirm="¿Desactivar esta importación? Sus datos dejarán de aparecer en las consultas de los usuarios, pero el registro permanecerá en este historial.">
                                        <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
                                        <input type="hidden" name="action" value="delete_excel_import">
                                        <input type="hidden" name="import_id" value="<?= h($importId) ?>">
                                        <button class="text-button deactivate-import-button" type="submit">Desactivar</button>
                                    </form>
                                <?php elseif ($estadoImportacion === 'DELETED'): ?>
                                    <span class="imports-active-label">Ya desactivada</span>
                                <?php else: ?>
                                    <span class="imports-active-label">No disponible</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php endif; ?>
</section>
