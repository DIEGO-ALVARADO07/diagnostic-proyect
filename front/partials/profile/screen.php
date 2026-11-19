<section class="module-heading">
    <div>
        <p class="eyebrow">DATOS DE LA CUENTA</p>
        <h1>Mi perfil</h1>
        <p>Consulta y actualiza la información de tu cuenta.</p>
    </div>
    <div class="profile-avatar"><?= h($usuarioInicial) ?></div>
</section>

<section class="panel module-panel profile-panel">
    <div class="profile-meta">
        <span class="role-badge role-<?= h($rol) ?>"><?= h($etiquetaRol) ?></span>
        <span class="muted">Usuario: <?= h($usuario['username'] ?? '') ?></span>
    </div>
    <form method="post" class="form-grid">
        <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
        <input type="hidden" name="action" value="update_profile">
        <label class="field"><span>Nombre completo</span><input name="full_name" value="<?= h($usuario['full_name'] ?? '') ?>" required maxlength="200"></label>
        <label class="field"><span>Correo electrónico</span><input name="email" type="email" value="<?= h($usuario['email'] ?? '') ?>" required maxlength="255"></label>
        <label class="field field-wide"><span>Nueva contraseña <small>(opcional)</small></span><input name="password" type="password" minlength="12" maxlength="256" placeholder="Déjala vacía para conservar la actual"><small>Si la cambias, debe tener al menos 12 caracteres.</small></label>
        <div class="form-actions"><button class="button button-primary" type="submit">Guardar cambios <span>→</span></button></div>
    </form>
</section>
