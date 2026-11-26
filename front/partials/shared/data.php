<?php
require_once __DIR__ . '/../../api_client.php';

header('Content-Type: application/json; charset=utf-8');
verificarAutenticacion();

function dashboardJson(int $status, array $data): void {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

function dashboardIdentifier($value, string $pattern): bool {
    return is_string($value) && preg_match($pattern, $value) === 1;
}

function dashboardFilters(array $input): array {
    $filters = [];
    foreach (['year', 'simulation', 'group', 'test_type'] as $key) {
        if (!isset($input[$key]) || $input[$key] === '') {
            continue;
        }
        if (!is_string($input[$key]) || strlen($input[$key]) > 255) {
            dashboardJson(422, ['detail' => 'Uno de los filtros enviados no es válido.']);
        }
        if ($key === 'year') {
            if (!ctype_digit($input[$key]) || (int) $input[$key] < 1900 || (int) $input[$key] > 2200) {
                dashboardJson(422, ['detail' => 'El año seleccionado no es válido.']);
            }
            $filters[$key] = (int) $input[$key];
        } else {
            $filters[$key] = $input[$key];
        }
    }
    // Periodo (AAAA-1 / AAAA-2) y momento de ESE, como en el dashboard.
    $period = $input['period'] ?? '';
    if ($period !== '') {
        if (!is_string($period) || !preg_match(DASHBOARD_PERIOD_PATTERN, $period)) {
            dashboardJson(422, ['detail' => 'El periodo seleccionado no es válido.']);
        }
        $filters['period'] = $period;
    }
    $moment = $input['moment'] ?? '';
    if ($moment !== '') {
        if (!is_string($moment) || !preg_match('/^[1-4]$/', $moment)) {
            dashboardJson(422, ['detail' => 'El momento seleccionado no es válido.']);
        }
        $filters['moment'] = (int) $moment;
    }

    return $filters;
}

function dashboardRequireCsrf(): void {
    $csrf = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!is_string($csrf) || empty($_SESSION['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $csrf)) {
        dashboardJson(403, ['detail' => 'La sesión de consulta venció. Actualiza la página e inténtalo de nuevo.']);
    }
}

function dashboardJsonBody(): array {
    $payload = json_decode(file_get_contents('php://input'), true);
    if (!is_array($payload)) {
        dashboardJson(400, ['detail' => 'La solicitud no es válida.']);
    }
    return $payload;
}

/** Reenvía la respuesta de la API tal cual (o un 502 si no respondió). */
function dashboardForward(array $respuesta): void {
    if (!empty($respuesta['error'])) {
        dashboardJson(502, ['detail' => 'No fue posible consultar el dashboard. Verifica que la API esté disponible.']);
    }
    dashboardJson(
        $respuesta['status'] ?: 502,
        is_array($respuesta['data']) ? $respuesta['data'] : ['detail' => 'La API devolvió una respuesta inválida.']
    );
}

const DASHBOARD_PERIOD_PATTERN = '/^\d{4}-[12]$/';
const DASHBOARD_COMPARE_PROGRAM_PATTERN = '/^([1-9][0-9]{0,9}|sin-programa)$/';

$role = $_SESSION['user']['role'] ?? '';
if (!in_array($role, ['instructor', 'superadmin'], true)) {
    dashboardJson(403, ['detail' => 'No tienes permiso para consultar el dashboard académico.']);
}

$resource = $_GET['resource'] ?? '';
if (!is_string($resource)) {
    dashboardJson(400, ['detail' => 'La consulta del dashboard no es válida.']);
}

// Asignar (o quitar con null) el programa de un estudiante de CORHUILA.
if ($resource === 'assign_program' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    dashboardRequireCsrf();
    $payload = dashboardJsonBody();
    $studentId = $payload['student_id'] ?? null;
    $programId = $payload['program_id'] ?? null;
    if (!is_int($studentId) || $studentId < 1 || ($programId !== null && (!is_int($programId) || $programId < 1))) {
        dashboardJson(422, ['detail' => 'Elige un estudiante y un programa válidos.']);
    }
    dashboardForward(llamarBackend(
        'PUT',
        'excel/dashboard/review/students/' . $studentId . '/program',
        ['program_id' => $programId]
    ));
}

// Recalcular el programa de todas las filas de CORHUILA.
if ($resource === 'resolve' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    dashboardRequireCsrf();
    dashboardForward(llamarBackend('POST', 'excel/dashboard/corhuila/resolve'));
}

if ($resource === 'student' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $payload = dashboardJsonBody();
    dashboardRequireCsrf();

    $importId = $payload['import_id'] ?? '';
    $document = $payload['document'] ?? '';
    if (!dashboardIdentifier($importId, '/^[a-f0-9-]{36}$/i') || !is_string($document) || $document === '' || strlen($document) > 80) {
        dashboardJson(422, ['detail' => 'No se pudo identificar la consulta del estudiante.']);
    }

    $respuesta = llamarBackend(
        'GET',
        'excel/dashboard/' . $importId . '/students/' . rawurlencode($document)
    );
    if (!empty($respuesta['error'])) {
        dashboardJson(502, ['detail' => 'No fue posible consultar el dashboard. Intenta de nuevo.']);
    }
    if ($respuesta['status'] < 200 || $respuesta['status'] >= 300) {
        dashboardJson($respuesta['status'] ?: 502, $respuesta['data'] ?: ['detail' => 'No fue posible consultar el estudiante.']);
    }

    $reference = bin2hex(random_bytes(16));
    if (!isset($_SESSION['dashboard_student_refs']) || !is_array($_SESSION['dashboard_student_refs'])) {
        $_SESSION['dashboard_student_refs'] = [];
    }
    $_SESSION['dashboard_student_refs'][$reference] = [
        'import_id' => $importId,
        'document' => $document,
    ];
    while (count($_SESSION['dashboard_student_refs']) > 20) {
        array_shift($_SESSION['dashboard_student_refs']);
    }

    dashboardJson(200, $respuesta['data'] + ['student_ref' => $reference]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    header('Allow: GET, POST');
    dashboardJson(405, ['detail' => 'Método no permitido.']);
}

if ($resource === 'active') {
    $endpoint = 'excel/dashboard/active';
    $params = [];
} elseif ($resource === 'compare') {
    // Dashboard principal: ESE frente a CORHUILA en un periodo.
    $params = [];
    $period = $_GET['period'] ?? '';
    if ($period !== '') {
        if (!dashboardIdentifier($period, DASHBOARD_PERIOD_PATTERN)) {
            dashboardJson(422, ['detail' => 'El periodo seleccionado no es válido.']);
        }
        $params['period'] = $period;
    }
    $moment = $_GET['moment'] ?? '';
    if ($moment !== '') {
        if (!dashboardIdentifier($moment, '/^[1-4]$/')) {
            dashboardJson(422, ['detail' => 'El momento seleccionado no es válido.']);
        }
        $params['moment'] = (int) $moment;
    }
    $programId = $_GET['program_id'] ?? '';
    if ($programId !== '') {
        if (!dashboardIdentifier($programId, DASHBOARD_COMPARE_PROGRAM_PATTERN)) {
            dashboardJson(422, ['detail' => 'El programa seleccionado no es válido.']);
        }
        $params['program_id'] = $programId;
    }
    $endpoint = 'excel/dashboard/compare';
} elseif ($resource === 'students') {
    // Módulo Estudiantes: estudiantes de los Excel por nivel, en un periodo
    // (por defecto el último) o en todo el histórico (period=all).
    $params = [];
    $period = $_GET['period'] ?? '';
    if ($period !== '') {
        if ($period !== 'all' && !dashboardIdentifier($period, DASHBOARD_PERIOD_PATTERN)) {
            dashboardJson(422, ['detail' => 'El periodo seleccionado no es válido.']);
        }
        $params['period'] = $period;
    }
    $level = $_GET['level'] ?? '';
    if ($level !== '') {
        if (!dashboardIdentifier($level, '/^([1-4]|sin-resultado)$/')) {
            dashboardJson(422, ['detail' => 'El nivel seleccionado no es válido.']);
        }
        $params['level'] = $level;
    }
    $programId = $_GET['program_id'] ?? '';
    if ($programId !== '') {
        if (!dashboardIdentifier($programId, DASHBOARD_COMPARE_PROGRAM_PATTERN)) {
            dashboardJson(422, ['detail' => 'El programa seleccionado no es válido.']);
        }
        $params['program_id'] = $programId;
    }
    $search = $_GET['search'] ?? '';
    if (!is_string($search) || mb_strlen($search) > 120) {
        dashboardJson(422, ['detail' => 'El texto de búsqueda es demasiado largo.']);
    }
    if (trim($search) !== '') {
        $params['search'] = trim($search);
    }
    $page = filter_var($_GET['page'] ?? 1, FILTER_VALIDATE_INT);
    if ($page === false || $page < 1) {
        dashboardJson(422, ['detail' => 'El número de página no es válido.']);
    }
    $params['page'] = $page;
    $params['page_size'] = 50;
    $endpoint = 'excel/dashboard/students';
} elseif ($resource === 'catalog') {
    $endpoint = 'excel/dashboard/catalog/programs';
    $params = [];
} elseif ($resource === 'without_program') {
    $params = [];
    $period = $_GET['period'] ?? '';
    if ($period !== '') {
        if (!dashboardIdentifier($period, DASHBOARD_PERIOD_PATTERN)) {
            dashboardJson(422, ['detail' => 'El periodo seleccionado no es válido.']);
        }
        $params['period'] = $period;
    }
    $endpoint = 'excel/dashboard/review/without-program';
} elseif (in_array($resource, ['overview', 'program'], true)) {
    $importId = $_GET['import_id'] ?? '';
    if (!dashboardIdentifier($importId, '/^[a-f0-9-]{36}$/i')) {
        dashboardJson(422, ['detail' => 'La importación seleccionada no es válida.']);
    }
    $params = dashboardFilters($_GET);

    if ($resource === 'overview') {
        $page = filter_var($_GET['page'] ?? 1, FILTER_VALIDATE_INT);
        if ($page === false || $page < 1) {
            dashboardJson(422, ['detail' => 'El número de página no es válido.']);
        }
        $params['page'] = $page;
        $params['page_size'] = 50;
        $endpoint = 'excel/dashboard/' . $importId;
    } else {
        $programId = $_GET['program_id'] ?? '';
        if (!dashboardIdentifier($programId, '/^[1-9][0-9]{0,9}$/')) {
            dashboardJson(422, ['detail' => 'El programa seleccionado no es válido.']);
        }
        $page = filter_var($_GET['page'] ?? 1, FILTER_VALIDATE_INT);
        if ($page === false || $page < 1) {
            dashboardJson(422, ['detail' => 'El número de página no es válido.']);
        }
        $search = $_GET['search'] ?? '';
        if (!is_string($search) || strlen($search) > 200) {
            dashboardJson(422, ['detail' => 'El texto de búsqueda es demasiado largo.']);
        }
        $params['page'] = $page;
        $params['page_size'] = 20;
        if ($search !== '') {
            $params['search'] = $search;
        }
        $endpoint = 'excel/dashboard/' . $importId . '/programs/' . $programId;
    }
} elseif ($resource === 'student' && isset($_GET['ref'])) {
    $reference = $_GET['ref'];
    if (!dashboardIdentifier($reference, '/^[a-f0-9]{32}$/') || empty($_SESSION['dashboard_student_refs'][$reference])) {
        dashboardJson(404, ['detail' => 'La referencia del estudiante ya no está disponible. Vuelve a seleccionarlo.']);
    }
    $studentReference = $_SESSION['dashboard_student_refs'][$reference];
    $endpoint = 'excel/dashboard/' . $studentReference['import_id'] . '/students/' . rawurlencode($studentReference['document']);
    $params = [];
} else {
    dashboardJson(404, ['detail' => 'La consulta solicitada no existe.']);
}

dashboardForward(llamarBackend('GET', $endpoint, $params));
