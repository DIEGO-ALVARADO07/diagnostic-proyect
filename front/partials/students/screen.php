<section class="module-heading">
    <div>
        <p class="eyebrow">SEGUIMIENTO ACADÉMICO</p>
        <h1>Estudiantes</h1>
        <p>Busca y filtra los perfiles de estudiantes disponibles.</p>
    </div>
    <span class="count-pill"><?= count($estudiantes) ?> estudiantes</span>
</section>

<section class="panel module-panel">
    <?php if ($errorUsuarios): ?>
        <div class="notice notice-error"><?= h($errorUsuarios) ?></div>
    <?php elseif ($estudiantes): ?>
        <div class="table-toolbar">
            <label class="search-box"><span>⌕</span><input type="search" data-table-search placeholder="Buscar por nombre, correo o usuario"></label>
            <span class="static-filter">♧ Estudiantes</span>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>ESTUDIANTE</th><th>USUARIO</th><th>ROL</th><th>ESTADO</th></tr></thead>
                <tbody>
                <?php foreach ($estudiantes as $item): ?>
                    <tr data-user-row data-role="estudiante" data-search="<?= h(strtolower(($item['full_name'] ?? '') . ' ' . ($item['email'] ?? '') . ' ' . ($item['username'] ?? ''))) ?>">
                        <td>
                            <div class="person-cell">
                                <span class="table-avatar"><?= h(inicialDe((string) ($item['full_name'] ?? $item['username'] ?? 'E'))) ?></span>
                                <span><strong><?= h($item['full_name'] ?? '') ?></strong><small><?= h($item['email'] ?? '') ?></small></span>
                            </div>
                        </td>
                        <td><?= h($item['username'] ?? '') ?></td>
                        <td><span class="role-badge role-estudiante">Estudiante</span></td>
                        <td><span class="active-state"><i></i>Activo</span></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php else: ?>
        <div class="empty-state"><span>♧</span><strong>No hay estudiantes para mostrar</strong><p>Los perfiles activos aparecerán aquí.</p></div>
    <?php endif; ?>
</section>
