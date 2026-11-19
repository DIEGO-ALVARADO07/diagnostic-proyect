<section class="module-heading">
    <div>
        <p class="eyebrow">NUEVO ACCESO</p>
        <h1>Crear cuenta</h1>
        <p>Registra un instructor o estudiante en la plataforma.</p>
    </div>
    <a class="button button-secondary" href="index.php?view=users">Volver a usuarios</a>
</section>

<section class="panel module-panel create-user-panel">
    <div class="form-intro">
        <span class="form-intro-icon">＋</span>
        <div><h2>Datos de la cuenta</h2><p>Los superadministradores no se crean desde este formulario.</p></div>
    </div>
    <form method="post" class="form-grid">
        <input type="hidden" name="csrf_token" value="<?= h($csrfToken) ?>">
        <input type="hidden" name="action" value="create_user">
        <label class="field"><span>Nombre completo</span><input name="full_name" required maxlength="200" placeholder="Ej. Laura Martínez"></label>
        <label class="field"><span>Nombre de usuario</span><input name="username" required minlength="3" maxlength="80" pattern="[A-Za-z0-9._-]+" placeholder="laura.martinez"></label>
        <label class="field"><span>Correo electrónico</span><input name="email" type="email" required maxlength="255" placeholder="laura@institucion.edu"></label>
        <label class="field"><span>Rol</span><select name="role" required><option value="instructor">Instructor</option><option value="estudiante">Estudiante</option></select></label>
        <label class="field field-wide"><span>Contraseña inicial</span><input name="password" type="password" required minlength="12" maxlength="256" placeholder="Mínimo 12 caracteres"><small>La contraseña debe tener al menos 12 caracteres.</small></label>
        <div class="form-actions"><button class="button button-primary" type="submit">Crear cuenta <span>→</span></button></div>
    </form>
</section>
