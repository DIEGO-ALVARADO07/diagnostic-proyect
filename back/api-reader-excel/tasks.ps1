<#
.SYNOPSIS
    Tareas comunes del backend: instalar, respaldar, migrar, crear el superadmin, probar y arrancar la API.

.DESCRIPTION
    Ejecuta siempre desde la carpeta del backend y con el Python del venv,
    sin necesidad de activar el entorno ni definir PYTHONPATH a mano.

.EXAMPLE
    .\tasks.ps1 install
    .\tasks.ps1 backup
    .\tasks.ps1 backup -Label antes-0008
    .\tasks.ps1 backup-daily
    .\tasks.ps1 schedule-backup -At 22:00
    .\tasks.ps1 unschedule-backup
    .\tasks.ps1 reset
    .\tasks.ps1 reset -IncludeUsers
    .\tasks.ps1 migrate
    .\tasks.ps1 bootstrap
    .\tasks.ps1 test
    .\tasks.ps1 run
    .\tasks.ps1 run -Port 8080
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "help", "install", "run", "test", "migrate", "bootstrap", "backup",
        "backup-daily", "schedule-backup", "unschedule-backup", "reset"
    )]
    [string]$Task = "help",

    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,

    # backup: carpeta de destino (por defecto %USERPROFILE%\respaldos\<base>),
    # etiqueta para el nombre del archivo y ruta de mysqldump si no está en el PATH.
    [string]$BackupDir = "",
    [string]$Label = "",
    [string]$MysqlDump = "",

    # backup-daily: conserva solo los N respaldos diarios más recientes (0 = todos).
    [int]$Keep = 0,
    # schedule-backup: hora diaria del respaldo (HH:mm).
    [string]$At = "22:00",
    # reset: borra también cuentas de usuario y sesiones.
    [switch]$IncludeUsers
)

$DailyTaskName = "Diagnostico academico - respaldo diario"

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

    "backup" {
        Assert-Venv
        Assert-EnvFile
        $backupArgs = @()
        if ($BackupDir) { $backupArgs += @("--output-dir", $BackupDir) }
        if ($Label) { $backupArgs += @("--label", $Label) }
        if ($MysqlDump) { $backupArgs += @("--mysqldump", $MysqlDump) }
        Invoke-Python -m scripts.backup_db @backupArgs
    }

    "backup-daily" {
        # Respaldo con etiqueta "diario" solo si los datos cambiaron desde la
        # última copia; si no, no crea otro archivo. Lo usa la tarea programada.
        Assert-Venv
        Assert-EnvFile
        $backupArgs = @("--if-changed", "--label", "diario")
        if ($Keep -gt 0) { $backupArgs += @("--keep", "$Keep") }
        if ($BackupDir) { $backupArgs += @("--output-dir", $BackupDir) }
        if ($MysqlDump) { $backupArgs += @("--mysqldump", $MysqlDump) }
        Write-Host ("[{0:yyyy-MM-dd HH:mm}] Respaldo diario" -f (Get-Date))
        Invoke-Python -m scripts.backup_db @backupArgs
    }

    "schedule-backup" {
        # Tarea de Windows que ejecuta "backup-daily" todos los días a la hora -At,
        # con tu usuario (así tiene APP_MASTER_KEY). Si el equipo estaba apagado
        # a esa hora, se ejecuta al encenderlo; si falla (por ejemplo, MySQL
        # apagado), reintenta cada hora hasta 6 veces. La salida queda en un log.
        Assert-Venv
        Assert-EnvFile
        $time = [datetime]::ParseExact($At, "HH:mm", $null)
        $logDir = Join-Path $env:USERPROFILE "respaldos"
        New-Item -ItemType Directory -Force $logDir | Out-Null
        $log = Join-Path $logDir "respaldo-diario.log"
        $script = Join-Path $BackendRoot "tasks.ps1"
        $extra = ""
        if ($Keep -gt 0) { $extra += " -Keep $Keep" }
        if ($BackupDir) { $extra += " -BackupDir '$BackupDir'" }
        if ($MysqlDump) { $extra += " -MysqlDump '$MysqlDump'" }
        # UTF-8 para que las tildes de los mensajes de Python queden bien en el log.
        $command = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; & '$script' backup-daily$extra *>> '$log'"
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command `"$command`"" `
            -WorkingDirectory $BackendRoot
        $trigger = New-ScheduledTaskTrigger -Daily -At $time
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
            -RestartCount 6 -RestartInterval (New-TimeSpan -Hours 1)
        Register-ScheduledTask -TaskName $DailyTaskName -Action $action -Trigger $trigger `
            -Settings $settings -Force `
            -Description "Respaldo diario de la base del diagnóstico académico; solo guarda copia si hubo cambios." | Out-Null
        Write-Host "Tarea programada: '$DailyTaskName' todos los días a las $At." -ForegroundColor Green
        Write-Host "Respaldos en %USERPROFILE%\respaldos\<base>; registro en $log"
        Write-Host "Si MySQL (Laragon) está apagado, la tarea reintenta cada hora (hasta 6 veces)."
    }

    "unschedule-backup" {
        if (Get-ScheduledTask -TaskName $DailyTaskName -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $DailyTaskName -Confirm:$false
            Write-Host "Se quitó la tarea '$DailyTaskName'. Los respaldos ya creados se conservan."
        } else {
            Write-Host "No hay una tarea '$DailyTaskName' registrada."
        }
    }

    "reset" {
        # Vacía la base para empezar el recorrido desde cero. Antes hace una
        # copia "antes-vaciar"; si falla, no borra nada.
        Assert-Venv
        Assert-EnvFile
        Write-Host "Se borrarán TODOS los datos académicos: importaciones de Excel, resultados," -ForegroundColor Yellow
        Write-Host "estudiantes, programas, cursos e inscripciones." -ForegroundColor Yellow
        if ($IncludeUsers) {
            Write-Host "También se borrarán las cuentas de usuario (luego: .\tasks.ps1 bootstrap)." -ForegroundColor Yellow
        } else {
            Write-Host "Las cuentas de usuario se conservan." -ForegroundColor Yellow
        }
        Write-Host "Antes se guarda una copia de seguridad con la etiqueta 'antes-vaciar'."
        $confirm = Read-Host "Escribe el nombre de la base de datos para confirmar"
        $resetArgs = @("--confirm", $confirm)
        if ($IncludeUsers) { $resetArgs += "--include-users" }
        Invoke-Python -m scripts.reset_db @resetArgs
    }

    "migrate" {
        Assert-Venv
        Assert-EnvFile
        Write-Host "Recuerda: haz antes una copia con .\tasks.ps1 backup" -ForegroundColor Yellow
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
