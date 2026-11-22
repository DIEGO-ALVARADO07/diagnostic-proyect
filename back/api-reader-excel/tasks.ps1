<#
.SYNOPSIS
    Tareas comunes del backend: instalar, migrar, crear el superadmin, probar y arrancar la API.

.DESCRIPTION
    Ejecuta siempre desde la carpeta del backend y con el Python del venv,
    sin necesidad de activar el entorno ni definir PYTHONPATH a mano.

.EXAMPLE
    .\tasks.ps1 install
    .\tasks.ps1 migrate
    .\tasks.ps1 bootstrap
    .\tasks.ps1 test
    .\tasks.ps1 run
    .\tasks.ps1 run -Port 8080
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("help", "install", "run", "test", "migrate", "bootstrap")]
    [string]$Task = "help",

    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$VenvPython = Join-Path $BackendRoot "venv\Scripts\python.exe"
$EnvFile = Join-Path $BackendRoot "core\.env"
$EnvExample = Join-Path $BackendRoot "core\.env.example"

Set-Location $BackendRoot
# Los paquetes core/, modules/, app/ y api/ se importan desde la raíz del backend.
$env:PYTHONPATH = $BackendRoot

function Assert-Venv {
    if (-not (Test-Path $VenvPython)) {
        throw "No existe el venv. Ejecuta primero: .\tasks.ps1 install"
    }
}

function Assert-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        throw "Falta core\.env. Copia la plantilla y complétala: Copy-Item core\.env.example core\.env"
    }
    # Solo comprueba si hay valores cifrados; no muestra ningún valor.
    # Acepta valores con o sin comillas: DB_USER=gAAAAAB... o DB_USER = "gAAAAAB..."
    $hasEncryptedValues = Select-String -Path $EnvFile -Pattern '=\s*["'']?gAAAAAB' -Quiet
    if ($hasEncryptedValues -and -not $env:APP_MASTER_KEY) {
        throw "core\.env tiene credenciales cifradas. Define APP_MASTER_KEY en esta terminal: `$env:APP_MASTER_KEY = '<clave>'"
    }
}

function Invoke-Python {
    # En Windows PowerShell 5.1, con "Stop", cualquier salida a stderr de un
    # ejecutable (unittest, uvicorn) se convierte en error. Se evalúa el código de salida.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $VenvPython @args
    }
    finally {
        $ErrorActionPreference = $previous
    }
    if ($LASTEXITCODE -ne 0) {
        throw "El comando terminó con código $LASTEXITCODE."
    }
}

function Read-BootstrapValue([string]$Name, [string]$Prompt, [switch]$Secret) {
    $current = [Environment]::GetEnvironmentVariable($Name)
    if ($current) { return }
    if ($Secret) {
        $secure = Read-Host -Prompt $Prompt -AsSecureString
        $value = [System.Net.NetworkCredential]::new("", $secure).Password
    } else {
        $value = Read-Host -Prompt $Prompt
    }
    [Environment]::SetEnvironmentVariable($Name, $value)
}

switch ($Task) {
    "help" {
        Get-Help $PSCommandPath -Detailed
    }

    "install" {
        if (-not (Test-Path $VenvPython)) {
            Write-Host "Creando venv..."
            python -m venv (Join-Path $BackendRoot "venv")
        }
        Invoke-Python -m pip install --upgrade pip
        Invoke-Python -m pip install -r requirements.txt
        if (-not (Test-Path $EnvFile)) {
            Write-Host "Recuerda crear core\.env a partir de core\.env.example." -ForegroundColor Yellow
        }
    }

    "test" {
        Assert-Venv
        # Evita que los logs INFO de la app se mezclen con el reporte de unittest.
        if (-not $env:LOG_LEVEL) { $env:LOG_LEVEL = "WARNING" }
        Invoke-Python -m unittest discover -s tests
    }

    "migrate" {
        Assert-Venv
        Assert-EnvFile
        Invoke-Python -m migrations
        Write-Host "Migraciones aplicadas." -ForegroundColor Green
    }

    "bootstrap" {
        Assert-Venv
        Assert-EnvFile
        $names = @(
            "BOOTSTRAP_SUPERADMIN_USERNAME",
            "BOOTSTRAP_SUPERADMIN_EMAIL",
            "BOOTSTRAP_SUPERADMIN_FULL_NAME",
            "BOOTSTRAP_SUPERADMIN_PASSWORD"
        )
        try {
            Read-BootstrapValue "BOOTSTRAP_SUPERADMIN_USERNAME" "Usuario del superadmin"
            Read-BootstrapValue "BOOTSTRAP_SUPERADMIN_EMAIL" "Correo del superadmin"
            Read-BootstrapValue "BOOTSTRAP_SUPERADMIN_FULL_NAME" "Nombre completo"
            Read-BootstrapValue "BOOTSTRAP_SUPERADMIN_PASSWORD" "Contraseña (mínimo 12 caracteres)" -Secret
            Invoke-Python -m modules.security.bootstrap
        }
        finally {
            # Las credenciales iniciales no deben quedar en la terminal.
            foreach ($name in $names) {
                [Environment]::SetEnvironmentVariable($name, $null)
            }
        }
    }

    "run" {
        Assert-Venv
        Assert-EnvFile
        Write-Host "API en http://${BindHost}:${Port}/docs (Ctrl+C para detener)" -ForegroundColor Cyan
        Invoke-Python -m uvicorn app:app --reload --host $BindHost --port $Port
    }
}
