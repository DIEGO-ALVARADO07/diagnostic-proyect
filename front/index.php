<?php
require_once 'api_client.php';
verificarAutenticacion();

function h($value): string {
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}

function inicialDe(string $texto): string {
    $inicial = function_exists('mb_substr')
        ? mb_substr($texto, 0, 1, 'UTF-8')
        : substr($texto, 0, 1);
    return function_exists('mb_strtoupper')
        ? mb_strtoupper($inicial, 'UTF-8')
        : strtoupper($inicial);
}

function mensajeDeRespuesta(array $respuesta, string $alternativo): string {
    if (!empty($respuesta['error'])) {
        return 'No fue posible comunicarse con la API. Verifica que el servicio esté disponible.';
    }

    $detail = $respuesta['data']['detail'] ?? $respuesta['data']['message'] ?? null;
    if (is_string($detail) && $detail !== '') {
        return $detail;
    }
    if (is_array($detail) && !empty($detail['message']) && is_string($detail['message'])) {
        return $detail['message'];
    }

    return $alternativo;
}

/**
 * Periodos en los que se puede subir un archivo: el actual y el anterior.
 *
 * Ejemplo: en noviembre de 2026 → 2026-2 y 2026-1; en enero de 2027 → 2027-1
 * y 2026-2 (para subir tarde los resultados del semestre que acaba de cerrar).
 * Así no se puede subir por error a un periodo viejo (2024, 2025) ni a uno
 * que todavía no empieza.
 */
function periodosDeCarga(?DateTimeImmutable $hoy = null): array {
    $hoy = $hoy ?? new DateTimeImmutable('now');
    $anio = (int) $hoy->format('Y');
    if ((int) $hoy->format('n') <= 6) {
        return [$anio . '-1', ($anio - 1) . '-2'];
    }
    return [$anio . '-2', $anio . '-1'];
}

function redirigir(string $vista): void {
    header('Location: index.php?view=' . rawurlencode($vista));
    exit;
}

if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

$rolSesion = $_SESSION['user']['role'] ?? '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $csrf = $_POST['csrf_token'] ?? '';
    if (!is_string($csrf) || !hash_equals($_SESSION['csrf_token'], $csrf)) {
        $_SESSION['flash'] = ['type' => 'error', 'message' => 'La sesión del formulario venció. Intenta de nuevo.'];
        redirigir('dashboard');
    }

    $accion = $_POST['action'] ?? '';
    if ($accion === 'update_profile') {
        $datos = [
            'full_name' => trim($_POST['full_name'] ?? ''),
            'email' => trim($_POST['email'] ?? ''),
        ];
        $password = $_POST['password'] ?? '';
        if ($password !== '') {
            $datos['password'] = $password;
        }

        $respuesta = llamarBackend('PATCH', 'users/me', $datos);
        if ($respuesta['status'] === 200) {
            $_SESSION['user'] = $respuesta['data'];
            $_SESSION['flash'] = ['type' => 'success', 'message' => 'Tu perfil se actualizó correctamente.'];
        } else {
            $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo actualizar el perfil.')];
        }
        redirigir('profile');
    }

    if ($accion === 'create_user' && $rolSesion === 'superadmin') {
        $datos = [
            'full_name' => trim($_POST['full_name'] ?? ''),
            'username' => trim($_POST['username'] ?? ''),
            'email' => trim($_POST['email'] ?? ''),
            'password' => $_POST['password'] ?? '',
            'role' => $_POST['role'] ?? '',
        ];
        $respuesta = llamarBackend('POST', 'users', $datos);
        if ($respuesta['status'] === 201) {
            $_SESSION['flash'] = ['type' => 'success', 'message' => 'La cuenta se creó correctamente.'];
        } else {
            $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo crear la cuenta.')];
        }
        redirigir('create_user');
    }

    if ($accion === 'deactivate_user' && $rolSesion === 'superadmin') {
        $userId = filter_var($_POST['user_id'] ?? null, FILTER_VALIDATE_INT);
        if ($userId === false || $userId === null || $userId < 1) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'La cuenta seleccionada no es válida.'];
        } else {
            $respuesta = llamarBackend('DELETE', 'users/' . $userId);
            if ($respuesta['status'] === 204) {
                $_SESSION['flash'] = ['type' => 'success', 'message' => 'La cuenta se desactivó correctamente.'];
            } else {
                $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo desactivar la cuenta.')];
            }
        }
        redirigir('users');
    }

    if ($accion === 'delete_excel_import' && $rolSesion === 'superadmin') {
        $importId = $_POST['import_id'] ?? '';
        if (!is_string($importId) || preg_match('/^[a-f0-9-]{36}$/i', $importId) !== 1) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'La importación seleccionada no es válida.'];
        } else {
            $respuesta = llamarBackend(
                'DELETE',
                'excel/dashboard/imports/' . rawurlencode($importId)
            );
            if ($respuesta['status'] === 204) {
                $_SESSION['flash'] = ['type' => 'success', 'message' => 'La importación se desactivó y ya no aparece en las consultas de los usuarios. Su estado permanece en el historial administrativo.'];
            } else {
                $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo eliminar la importación.')];
            }
        }
        redirigir('imports');
    }

    if ($accion === 'restore_excel_import' && $rolSesion === 'superadmin') {
        $importId = $_POST['import_id'] ?? '';
        if (!is_string($importId) || preg_match('/^[a-f0-9-]{36}$/i', $importId) !== 1) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'La importación seleccionada no es válida.'];
        } else {
            $respuesta = llamarBackend(
                'POST',
                'excel/dashboard/imports/' . rawurlencode($importId) . '/restore'
            );
            if ($respuesta['status'] === 200) {
                $_SESSION['flash'] = ['type' => 'success', 'message' => (string) ($respuesta['data']['message'] ?? 'La importación se restauró.')];
            } else {
                $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo restaurar la importación.')];
            }
        }
        redirigir('imports');
    }

    if ($accion === 'upload_excel' && in_array($rolSesion, ['instructor', 'superadmin'], true)) {
        $uploadedFile = $_FILES['file'] ?? null;
        $fuente = $_POST['source'] ?? '';
        $periodo = $_POST['period'] ?? '';
        if (!in_array($fuente, ['ESE', 'CORHUILA'], true) || !is_string($periodo) || preg_match('/^\d{4}-[12]$/', $periodo) !== 1) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'Elige la prueba (ESE o CORHUILA) y el periodo de la carga.'];
        } elseif (!in_array($periodo, periodosDeCarga(), true)) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'Solo se pueden subir archivos del periodo actual o del anterior (' . implode(' o ', periodosDeCarga()) . ').'];
        } elseif (!is_array($uploadedFile) || ($uploadedFile['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'Selecciona un archivo Excel válido para continuar.'];
        } elseif (($uploadedFile['size'] ?? 0) > 30 * 1024 * 1024) {
            $_SESSION['flash'] = ['type' => 'error', 'message' => 'El archivo supera el límite permitido de 30 MB.'];
        } else {
            $respuesta = llamarBackendMultipart(
                'excel/dashboard/import',
                ['source' => $fuente, 'period' => $periodo],
                [
                    'field' => 'file',
                    'tmp_name' => $uploadedFile['tmp_name'],
                    'type' => $uploadedFile['type'] ?? '',
                    'name' => $uploadedFile['name'] ?? '',
                ]
            );
            if ($respuesta['status'] === 200) {
                $importacion = $respuesta['data'];
                if (($importacion['status'] ?? '') === 'ACTIVE') {
                    $_SESSION['flash'] = [
                        'type' => 'success',
                        'message' => 'El archivo de ' . $fuente . ' (' . $periodo . ') se importó y sus resultados ya están disponibles en el dashboard.',
                    ];
                } else {
                    $_SESSION['flash'] = [
                        'type' => 'success',
                        'message' => 'Este archivo ya existe como una importación histórica. No se activó de nuevo; el dashboard conserva la versión activa actual.',
                    ];
                }
            } else {
                $_SESSION['flash'] = ['type' => 'error', 'message' => mensajeDeRespuesta($respuesta, 'No se pudo importar el archivo Excel.')];
            }
        }
        redirigir('dashboard');
    }

    $_SESSION['flash'] = ['type' => 'error', 'message' => 'No tienes permiso para realizar esa acción.'];
    redirigir('dashboard');
}

$respuestaPerfil = llamarBackend('GET', 'users/me');
$errorCarga = null;
$usuario = $_SESSION['user'] ?? [];
if ($respuestaPerfil['status'] === 200 && is_array($respuestaPerfil['data'])) {
    $usuario = $respuestaPerfil['data'];
    $_SESSION['user'] = $usuario;
} else {
    $errorCarga = mensajeDeRespuesta($respuestaPerfil, 'No fue posible cargar tu perfil.');
}

$rol = $usuario['role'] ?? '';
$etiquetasRol = [
    'superadmin' => 'Super administrador',
    'instructor' => 'Instructor',
    'estudiante' => 'Estudiante',
];
$etiquetaRol = $etiquetasRol[$rol] ?? 'Cuenta';

$vistas = [
    'dashboard' => [
        'title' => 'Dashboard',
        'screen' => 'dashboard/screen.php',
        'style' => ['shared/style.css', 'dashboard/style.css'],
        'script' => 'partials/dashboard/js/main.js',
    ],
    'ese' => [
        'title' => 'ESE',
        'screen' => 'ese/screen.php',
        'style' => 'shared/style.css',
        'script' => 'partials/ese/js/main.js',
    ],
    'corhuila' => [
        'title' => 'CORHUILA',
        'screen' => 'corhuila/screen.php',
        'style' => ['shared/style.css', 'dashboard/style.css', 'corhuila/style.css'],
        'script' => 'partials/corhuila/js/main.js',
    ],
    'users' => [
        'title' => 'Usuarios',
        'screen' => 'users/screen.php',
        'style' => 'users/style.css',
    ],
    'create_user' => [
        'title' => 'Crear cuenta',
        'screen' => 'create_user/screen.php',
        'style' => 'create_user/style.css',
    ],
    'students' => [
        'title' => 'Estudiantes',
        'screen' => 'students/screen.php',
        'style' => ['shared/style.css', 'students/style.css'],
        'script' => 'partials/students/js/main.js',
    ],
    'courses' => [
        'title' => 'Cursos',
        'screen' => 'courses/screen.php',
        'style' => ['shared/style.css', 'students/style.css', 'courses/style.css'],
        'script' => 'partials/courses/js/main.js',
    ],
    'courses_deleted' => [
        'title' => 'Cursos eliminados',
        'screen' => 'courses_deleted/screen.php',
        'style' => ['shared/style.css', 'students/style.css', 'courses/style.css', 'courses_deleted/style.css'],
        'script' => 'partials/courses_deleted/js/main.js',
    ],
    'report' => [
        'title' => 'Importar Excel',
        'screen' => 'report/screen.php',
        'style' => 'report/style.css',
    ],
    'profile' => [
        'title' => 'Mi perfil',
        'screen' => 'profile/screen.php',
        'style' => 'profile/style.css',
    ],
    'imports' => [
        'title' => 'Importaciones',
        'screen' => 'imports/screen.php',
        'style' => 'imports/style.css',
    ],
];

$menuPorRol = [
    'superadmin' => [
        ['view' => 'dashboard', 'label' => 'Dashboard', 'icon' => '⌂'],
        ['view' => 'ese', 'label' => 'ESE', 'icon' => '▥'],
        ['view' => 'corhuila', 'label' => 'CORHUILA', 'icon' => '◧'],
        ['view' => 'report', 'label' => 'Importar Excel', 'icon' => '↑'],
        ['view' => 'students', 'label' => 'Estudiantes', 'icon' => '♧'],
        ['view' => 'courses', 'label' => 'Cursos', 'icon' => '◫'],
        ['view' => 'courses_deleted', 'label' => 'Cursos eliminados', 'icon' => '⟲'],
        ['view' => 'imports', 'label' => 'Importaciones', 'icon' => '▤'],
        ['view' => 'users', 'label' => 'Usuarios', 'icon' => '♧'],
        ['view' => 'create_user', 'label' => 'Crear cuenta', 'icon' => '＋'],
        ['view' => 'profile', 'label' => 'Mi perfil', 'icon' => '○'],
    ],
    'instructor' => [
        ['view' => 'dashboard', 'label' => 'Dashboard', 'icon' => '⌂'],
        ['view' => 'ese', 'label' => 'ESE', 'icon' => '▥'],
        ['view' => 'corhuila', 'label' => 'CORHUILA', 'icon' => '◧'],
        ['view' => 'report', 'label' => 'Importar Excel', 'icon' => '↑'],
        ['view' => 'students', 'label' => 'Estudiantes', 'icon' => '♧'],
        ['view' => 'courses', 'label' => 'Cursos', 'icon' => '◫'],
        ['view' => 'profile', 'label' => 'Mi perfil', 'icon' => '○'],
    ],
    'estudiante' => [
        ['view' => 'profile', 'label' => 'Mi perfil', 'icon' => '○'],
    ],
];

$menu = $menuPorRol[$rol] ?? $menuPorRol['estudiante'];
$vistasPermitidas = array_column($menu, 'view');
$vistaSolicitada = $_GET['view'] ?? 'dashboard';
$vistaSolicitada = is_string($vistaSolicitada) ? $vistaSolicitada : 'dashboard';
if (!in_array($vistaSolicitada, $vistasPermitidas, true)) {
    if (isset($vistas[$vistaSolicitada])) {
        $_SESSION['flash'] = ['type' => 'error', 'message' => 'No tienes permiso para abrir esa sección.'];
    }
    $vistaSolicitada = $vistasPermitidas[0] ?? 'profile';
}

$vistaActual = $vistas[$vistaSolicitada];
$rutaPantalla = __DIR__ . '/partials/' . $vistaActual['screen'];
$usuarioNombre = $usuario['full_name'] ?? $usuario['username'] ?? 'Usuario';
$usuarioInicial = inicialDe((string) $usuarioNombre);
$csrfToken = $_SESSION['csrf_token'];

$flash = $_SESSION['flash'] ?? null;
unset($_SESSION['flash']);

$usuarios = [];
$errorUsuarios = null;
if ($vistaSolicitada === 'users') {
    $respuestaUsuarios = llamarBackend('GET', 'users', ['limit' => 100]);
    if ($respuestaUsuarios['status'] === 200 && is_array($respuestaUsuarios['data'])) {
        $usuarios = $respuestaUsuarios['data'];
    } else {
        $errorUsuarios = mensajeDeRespuesta($respuestaUsuarios, 'No se pudo cargar el listado de usuarios.');
    }
}

$estudiantes = array_values(array_filter($usuarios, static function ($item): bool {
    return ($item['role'] ?? '') === 'estudiante';
}));
$cantidadInstructores = count(array_filter($usuarios, static function ($item): bool {
    return ($item['role'] ?? '') === 'instructor';
}));

$importaciones = [];
$errorImportaciones = null;
if ($vistaSolicitada === 'imports' && $rol === 'superadmin') {
    $respuestaImportaciones = llamarBackend('GET', 'excel/dashboard/admin/imports', ['limit' => 100]);
    if (
        $respuestaImportaciones['status'] === 200
        && is_array($respuestaImportaciones['data']['imports'] ?? null)
    ) {
        $importaciones = $respuestaImportaciones['data']['imports'];
    } else {
        $errorImportaciones = mensajeDeRespuesta(
            $respuestaImportaciones,
            'No se pudo cargar el historial de importaciones.'
        );
    }
}

?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= h($vistaActual['title']) ?> | Diagnóstico académico</title>
    <link rel="stylesheet" href="dashboard.css">
    <?php foreach ((array) $vistaActual['style'] as $estilo): ?>
        <link rel="stylesheet" href="partials/<?= h($estilo) ?>">
    <?php endforeach; ?>
    <script src="dashboard.js" defer></script>
    <?php if (!empty($vistaActual['script'])): ?>
        <script type="module" src="<?= h($vistaActual['script']) ?>"></script>
    <?php endif; ?>
</head>
<body>
<div class="app-shell">
    <aside class="sidebar">
        <a class="brand" href="index.php?view=dashboard" aria-label="Diagnóstico académico, inicio">
            <span class="brand-mark">D</span>
            <span><strong>Diagnóstico</strong><small>Panel académico</small></span>
        </a>

        <div class="sidebar-label">MENÚ PRINCIPAL</div>
        <nav class="side-nav" aria-label="Navegación principal">
            <?php foreach ($menu as $item): ?>
                <a class="nav-link<?= $vistaSolicitada === $item['view'] ? ' active' : '' ?>" href="index.php?view=<?= h($item['view']) ?>"<?= $vistaSolicitada === $item['view'] ? ' aria-current="page"' : '' ?>>
                    <span class="nav-icon"><?= h($item['icon']) ?></span><?= h($item['label']) ?>
                </a>
            <?php endforeach; ?>
        </nav>

        <div class="sidebar-bottom">
            <div class="account-card">
                <div class="account-avatar"><?= h($usuarioInicial) ?></div>
                <div><strong><?= h($usuarioNombre) ?></strong><small><?= h($etiquetaRol) ?></small></div>
            </div>
            <a class="logout-link" href="logout.php"><span>↪</span>Cerrar sesión</a>
        </div>
    </aside>

    <main class="main-content">
        <header class="topbar">
            <div class="mobile-brand">
                <button type="button" class="mobile-menu-toggle" data-menu-toggle aria-label="Abrir menú">☰</button>
                <span class="brand-mark">D</span><strong>Diagnóstico</strong>
            </div>
            <div class="breadcrumb">Espacio de trabajo <span>/</span> <strong><?= h($vistaActual['title']) ?></strong></div>
            <div class="topbar-user">
                <div class="avatar"><?= h($usuarioInicial) ?></div>
                <div class="topbar-user-copy"><strong><?= h($usuarioNombre) ?></strong><span><?= h($etiquetaRol) ?></span></div>
            </div>
        </header>

        <div class="page-content">
            <?php if ($flash): ?>
                <div class="notice notice-<?= h($flash['type'] ?? 'error') ?>" role="status"><?= h($flash['message'] ?? '') ?></div>
            <?php endif; ?>
            <?php if ($errorCarga): ?>
                <div class="notice notice-error" role="alert"><?= h($errorCarga) ?></div>
            <?php endif; ?>

            <?php require $rutaPantalla; ?>

            <footer class="page-footer"><span>Diagnóstico académico</span><span>Gestión de perfiles y lectura de reportes</span></footer>
        </div>
    </main>
</div>
</body>
</html>
