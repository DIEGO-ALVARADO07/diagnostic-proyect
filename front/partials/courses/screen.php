<?php
// Módulo Cursos (fase 13b): Nivel → Curso (materia, nombre, descripción y
// metodología) → Estudiantes. Los 4 niveles se pintan aquí; js/main.js los
// llena con GET /courses. Los eliminados se ven en "Cursos eliminados" (superadmin).
$materias = [
    'lectura_critica' => 'Lectura crítica',
    'competencias_ciudadanas' => 'Competencias ciudadanas',
    'razonamiento_cuantitativo' => 'Razonamiento cuantitativo',
    'ingles' => 'Inglés',
];
?>
<div class="dashboard-app courses-app"
     data-courses
     data-csrf-token="<?= h($csrfToken) ?>">
    <section class="module-heading">
        <div>
            <p class="eyebrow">SEGUIMIENTO ACADÉMICO</p>
            <h1>Cursos</h1>
            <p>Crea un curso por nivel y materia, y agrega de una vez a los estudiantes que tienen ese nivel en esa materia.</p>
        </div>
        <span class="count-pill" data-courses-total>— cursos</span>
    </section>

    <section class="panel courses-create" aria-label="Crear curso">
        <div class="filter-heading">
            <div><p class="eyebrow">NUEVO CURSO</p><h2>Crear curso</h2></div>
        </div>
        <form class="courses-create-form" data-course-form novalidate>
            <label class="filter-field"><span>Nivel</span>
                <select name="level" data-course-level aria-label="Nivel del curso">
                    <?php foreach ([1, 2, 3, 4] as $nivel): ?>
                        <option value="<?= $nivel ?>">Nivel <?= $nivel ?></option>
                    <?php endforeach; ?>
                </select>
            </label>
            <label class="filter-field"><span>Materia evaluada</span>
                <select name="competency" data-course-competency aria-label="Materia del curso">
                    <?php foreach ($materias as $clave => $materia): ?>
                        <option value="<?= h($clave) ?>"><?= h($materia) ?></option>
                    <?php endforeach; ?>
                </select>
            </label>
            <label class="filter-field courses-name"><span>Nombre del curso</span><input type="text" name="name" maxlength="150" required placeholder="Ej.: Comprensión de textos argumentativos" data-course-name></label>
            <label class="filter-field courses-text"><span>Descripción</span><textarea name="description" rows="3" maxlength="2000" required placeholder="Qué se trabaja en el curso y qué se espera lograr." data-course-description></textarea></label>
            <label class="filter-field courses-text"><span>Metodología</span><textarea name="methodology" rows="3" maxlength="2000" required placeholder="Cómo se va a trabajar: talleres, simulacros, tutorías…" data-course-methodology></textarea></label>
            <div class="courses-create-actions">
                <button type="submit" class="button button-primary" data-course-submit><span>＋</span> Crear curso</button>
            </div>
        </form>
        <p class="courses-status" data-courses-status role="status" aria-live="polite"></p>
    </section>

    <section class="panel courses-period" aria-label="Periodo para agregar estudiantes">
        <label class="filter-field"><span>Agregar estudiantes según el nivel del periodo</span><select data-courses-period aria-label="Periodo del nivel"></select></label>
        <p>El botón <strong>Agregar estudiantes</strong> de cada curso inscribe a todos los que tienen el nivel del curso <strong>en su materia</strong> en este periodo. Ejemplo: Inglés de Nivel 1 recibe a los que tienen A1 en Inglés. Los que ya están inscritos no se repiten.</p>
    </section>

    <div class="students-status" data-courses-loading role="status">
        <span class="loading-spinner" aria-hidden="true"></span>
        <strong>Cargando cursos…</strong>
    </div>
    <div class="students-status dashboard-error" data-courses-error hidden role="alert">
        <span class="status-symbol">!</span>
        <strong>No fue posible cargar los cursos</strong>
        <p data-courses-error-message>Verifica la conexión con la API e inténtalo nuevamente.</p>
        <button type="button" class="button button-secondary" data-courses-retry>Reintentar</button>
    </div>

    <div class="course-levels" data-courses-content hidden>
        <?php foreach ([1, 2, 3, 4] as $nivel): ?>
            <section class="panel course-level level-group-<?= $nivel ?>" data-course-level-section="<?= $nivel ?>">
                <button type="button" class="course-level-toggle" data-course-level-toggle aria-expanded="false">
                    <span class="course-level-mark">N<?= $nivel ?></span>
                    <span class="course-level-text">
                        <strong>Nivel <?= $nivel ?></strong>
                        <small data-course-level-summary>—</small>
                    </span>
                    <span class="course-level-chevron" aria-hidden="true">▾</span>
                </button>
                <div class="course-level-body" data-course-level-body hidden>
                    <div class="course-level-available" data-course-level-available></div>
                    <div class="course-list" data-course-list></div>
                    <p class="course-empty" data-course-empty hidden>Aún no hay cursos de Nivel <?= $nivel ?>. Créalo arriba eligiendo este nivel y la materia.</p>
                </div>
            </section>
        <?php endforeach; ?>
    </div>
</div>
