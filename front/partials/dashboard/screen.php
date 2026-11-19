<?php $primerNombre = explode(' ', trim((string) $usuarioNombre))[0] ?: $usuarioNombre; ?>
<section class="dashboard-welcome">
    <div>
        <p class="eyebrow">TU ESPACIO DE TRABAJO</p>
        <h1>Hola, <?= h($primerNombre) ?> <span class="welcome-spark">✦</span></h1>
        <p class="welcome-copy">Este será el resumen de tu actividad y tus reportes.</p>
    </div>
    <div class="session-badge"><span></span>Sesión activa</div>
</section>

<section class="dashboard-overview panel" aria-labelledby="overview-title">
    <div class="overview-heading">
        <div>
            <p class="eyebrow">VISTA GENERAL</p>
            <h2 id="overview-title">Resumen de actividad</h2>
        </div>
        <span class="overview-period">Panel académico</span>
    </div>
    <div class="chart-placeholder">
        <div class="chart-guides" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
        <div class="chart-empty">
            <span class="chart-icon" aria-hidden="true">▥</span>
            <h3>Aquí aparecerán tus gráficos</h3>
            <p>Cuando se procesen los primeros reportes de Excel, encontrarás aquí el resumen de los datos.</p>
        </div>
    </div>
</section>
