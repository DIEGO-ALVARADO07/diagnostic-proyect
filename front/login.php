<?php
require_once 'api_client.php';

// Si ya tiene token activo, lo mandamos directo al panel
if (!empty($_SESSION['token'])) {
    header('Location: index.php'); // [CAMBIO 1] Quitamos la '/' inicial por si entras por localhost/front/
    exit;
}

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? ''); // Agregamos trim() para limpiar espacios accidentales
    $password = $_POST['password'] ?? '';

    // Llamamos al endpoint de login de tu backend (sin requerir token previo)
    $respuesta = llamarBackend('POST', 'auth/login', [
        'username' => $username,
        'password' => $password
    ], false);

    // [CAMBIO 2] Cambiamos 'token' por 'access_token' que es como lo devuelve tu modelo LoginResponse
    if ($respuesta['status'] === 200 && !empty($respuesta['data']['access_token'])) {
        session_regenerate_id(true); // Seguridad contra fijación de sesión
        
        // [CAMBIO 3] Guardamos el 'access_token' y también los datos de 'user' que te envía FastAPI
        $_SESSION['token'] = $respuesta['data']['access_token'];
        $_SESSION['user']  = $respuesta['data']['user'] ?? null;
        
        header('Location: index.php'); // [CAMBIO 1] Sin '/' inicial para evitar errores de ruta en Laragon
        exit;
    } else {
        // [CAMBIO 4] FastAPI devuelve los errores en 'detail' (ej. {"detail": "Incorrect username or password"})
        $error = $respuesta['data']['detail'] ?? $respuesta['data']['message'] ?? 'Credenciales incorrectas.';
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Iniciar Sesión</title>
</head>
<body style="font-family: sans-serif; max-width: 400px; margin: 60px auto;">
    <h2>Iniciar Sesión</h2>
    
    <?php if ($error): ?>
        <p style="color: red;"><?= htmlspecialchars($error) ?></p>
    <?php endif; ?>

    <form method="POST" action="login.php">
        <div style="margin-bottom: 10px;">
            <label>User:</label><br>
            <input type="text" name="username" required style="width: 100%; padding: 8px;">
        </div>
        <div style="margin-bottom: 15px;">
            <label>Contraseña:</label><br>
            <input type="password" name="password" required style="width: 100%; padding: 8px;">
        </div>
        <button type="submit" style="padding: 10px 20px;">Entrar</button>
    </form>
</body>
</html>
