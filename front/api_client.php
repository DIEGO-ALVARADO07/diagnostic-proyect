<?php
// 1. Configurar duración de la sesión a 8 horas (28800 segundos)
$duracion = 28800;
ini_set('session.gc_maxlifetime', $duracion);
session_set_cookie_params([
    'lifetime' => $duracion,
    'path' => '/',
    'httponly' => true, // Protege la cookie contra acceso por JS
    'samesite' => 'Lax'
]);

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// URL base de tu backend (Cámbiala por la tuya)
define('API_BASE_URL', 'http://127.0.0.1:8000');

/**
 * Redirige al login limpiando la sesión (soporta peticiones normales y HTMX)
 */
function forzarLogout(): void {
    $_SESSION = [];
    if (ini_get("session.use_cookies")) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params["path"], $params["domain"], $params["secure"], $params["httponly"]);
    }
    session_destroy();

    if (!empty($_SERVER['HTTP_X_DASHBOARD_REQUEST'])) {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['detail' => 'La sesión expiró. Inicia sesión de nuevo.']);
        exit;
    }

    // Si la petición vino desde HTMX, usamos HX-Redirect para redirigir toda la ventana
    if (!empty($_SERVER['HTTP_HX_REQUEST'])) {
        header('HX-Redirect: /front/login.php');
    } else {
        header('Location: /front/login.php');
    }
    exit;
}

/**
 * Verifica que el usuario tenga un token guardado en el frontend
 */
function verificarAutenticacion(): void {
    if (empty($_SESSION['token'])) {
        forzarLogout();
    }
}

/**
 * Realiza peticiones HTTP (GET, POST, PUT, DELETE) a tu API Backend
 */
function llamarBackend(string $metodo, string $endpoint, array $datos = [], bool $requiereAuth = true): array {
    $url = rtrim(API_BASE_URL, '/') . '/' . ltrim($endpoint, '/');

    if ($metodo === 'GET' && !empty($datos)) {
        $url .= '?' . http_build_query($datos);
    }

    $headers = [
        'Accept: application/json',
        'Content-Type: application/json'
    ];

    if ($requiereAuth && !empty($_SESSION['token'])) {
        $headers[] = 'Authorization: Bearer ' . $_SESSION['token'];
    }

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, strtoupper($metodo));
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);

    if ($metodo !== 'GET' && !empty($datos)) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($datos));
    }

    return finalizarPeticionBackend($ch, $requiereAuth);
}

/**
 * Envía un archivo y campos de formulario sin establecer manualmente el boundary multipart.
 */
function llamarBackendMultipart(string $endpoint, array $campos, array $archivo, bool $requiereAuth = true): array {
    $url = rtrim(API_BASE_URL, '/') . '/' . ltrim($endpoint, '/');
    $headers = ['Accept: application/json'];

    if ($requiereAuth && !empty($_SESSION['token'])) {
        $headers[] = 'Authorization: Bearer ' . $_SESSION['token'];
    }

    $campos[$archivo['field']] = new CURLFile(
        $archivo['tmp_name'],
        $archivo['type'] ?: 'application/octet-stream',
        $archivo['name']
    );

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $campos);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);

    return finalizarPeticionBackend($ch, $requiereAuth);
}

/**
 * Normaliza la respuesta y gestiona errores de conexión y tokens vencidos.
 */
function finalizarPeticionBackend($ch, bool $requiereAuth): array {
    $respuesta = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = $respuesta === false ? curl_error($ch) : null;
    curl_close($ch);

    if ($requiereAuth && $httpCode === 401) {
        forzarLogout();
    }

    $data = is_string($respuesta) && $respuesta !== ''
        ? json_decode($respuesta, true)
        : [];
    if (!is_array($data)) {
        $data = [];
        if ($error === null && $respuesta !== false && $respuesta !== '') {
            $error = 'La API devolvió una respuesta que no se pudo interpretar.';
        }
    }

    return [
        'status' => $httpCode,
        'data'   => $data,
        'error'  => $error
    ];
}
