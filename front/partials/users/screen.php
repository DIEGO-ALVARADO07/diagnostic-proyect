<section class="module-heading">
    <div>
        <p class="eyebrow">ADMINISTRACIÓN</p>
        <h1>Usuarios</h1>
        <p>Consulta y administra las cuentas activas de la plataforma.</p>
    </div>
    <a class="button button-primary" href="index.php?view=create_user"><span>＋</span> Crear cuenta</a>
</section>

<section class="panel module-panel">
    <div class="list-summary">
        <div><strong><?= count($usuarios) ?></strong><span>cuentas en este listado</span></div>
        <div><strong><?= count($estudiantes) ?></strong><span>estudiantes</span></div>
        <div><strong><?= $cantidadInstructores ?></strong><span>instructores</span></div>
    </div>

    <?php if ($errorUsuarios): ?>
        <div class="notice notice-error"><?= h($errorUsuarios) ?></div>
    <?php elseif ($usuarios): ?>
        <div class="table-toolbar">
            <label class="search-box"><span>⌕</span><input type="search" data-table-search placeholder="Buscar por nombre, correo o usuario"></label>
            <select class="select-control" data-role-filter aria-label="Filtrar por rol">
                <option value="">Todos los roles</option>
                <option value="instructor">Instructores</option>
                <option value="estudiante">Estudiantes</option>
                <option value="superadmin">Superadministradores</option>
            </select>
        </div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>PERSONA</th><th>USUARIO</th><th>ROL</th><th>ESTADO</th><th>ACCIÓN</th></tr></thead>
                <tbody>
                <?php foreach ($usuarios as $item): ?>
                    <tr data-user-row data-role="<?= h($item['role'] ?? '') ?>" data-search="<?= h(strtolower(($item['full_name'] ?? '') . ' ' . ($item['email'] ?? '') . ' ' . ($item['username'] ?? ''))) ?>">
                        <td>
                            <div class="person-cell">
                                <span class="table-avatar"><?= h(inicialDe((string) ($item['full_name'] ?? $item['username'] ?? 'U'))) ?></span>
                                <span><strong><?= h($item['full_name'] ?? '') ?></strong><small><?= h($item['email'] ?? '') ?></small></span>
                            </div>
                        </td>
                        <td><?= h($item['username'] ?? '') ?></td>
                        <td><span class="role-badge role-<?= h($item['role'] ?? '') ?>"><?= h($etiquetasRol[$item['role'] ?? ''] ?? ($item['role'] ?? '')) ?></span></td>
                        <td><span class="active-state"><i></i>Activo</span></td>
                        <td>
                            <?php if (($item['id'] ?? null) !== ($usuario['id'] ?? null)): ?>
                                <form method="post" class="inline-form" data-confirm-title="¿Desactivar esta cuenta?" data-confirm-label="Desactivar cuenta" data-confirm="La persona perderá el acceso a la plataforma.">
                                    <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
                                    <input type="hidden" name="action" value="deactivate_user">
                                    <input type="hidden" name="user_id" value="<?= h($item['id'] ?? '') ?>">
                                    <button class="text-button danger-text" type="submit">Desactivar</button>
                                </form>
                            <?php else: ?>
                                <span class="muted">Tu cuenta</span>
                            <?php endif; ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        <p class="table-footnote">Se muestran hasta 100 usuarios activos.</p>
    <?php else: ?>
        <div class="empty-state"><span>▤</span><strong>Aún no hay cuentas para mostrar</strong><p>Crea la primera cuenta desde la sección de administración.</p></div>
    <?php endif; ?>
</section>
