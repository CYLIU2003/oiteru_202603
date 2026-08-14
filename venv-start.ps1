<#
.SYNOPSIS
Starts OITERU using a project-local Python virtual environment.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\venv-start.ps1 test
#>

param(
    [ValidateSet("parent-mysql", "sub-parent", "unit", "test")]
    [string]$Mode = "parent-mysql"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$EnvFile = Join-Path $PSScriptRoot ".env"

function Find-SystemPython {
    foreach ($candidate in @("py", "python3", "python")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return @($command.Source)
        }
    }
    return $null
}

function Ensure-ProjectVenv {
    if (Test-Path $PythonPath) {
        $usable = $false
        try {
            & $PythonPath --version *> $null
            $usable = ($LASTEXITCODE -eq 0)
        } catch {
            $usable = $false
        }
        if ($usable) {
            return
        }
        Write-Warning "Existing .venv is stale; rebuilding it."
    }

    $systemPython = Find-SystemPython
    if (-not $systemPython) {
        throw "Python 3.12+ was not found. Install Python and enable 'Add python.exe to PATH', then run this command again."
    }

    Write-Host "Creating .venv with $systemPython ..."
    & $systemPython -m venv --clear (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PythonPath)) {
        throw "Failed to create .venv. Ensure the selected Python includes the venv module."
    }

    & $PythonPath -m pip install --upgrade pip
    & $PythonPath -m pip install -r (Join-Path $PSScriptRoot "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install development dependencies."
    }
}

function Require-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        throw ".env was not found. Copy .env.example to .env and configure MySQL credentials."
    }
}

Ensure-ProjectVenv

switch ($Mode) {
    "parent-mysql" {
        Require-EnvFile
        & $PythonPath db_server.py
        exit $LASTEXITCODE
    }
    "sub-parent" {
        Require-EnvFile
        $env:DB_TYPE = "mysql"
        & $PythonPath server.py
        exit $LASTEXITCODE
    }
    "unit" {
        & $PythonPath unit.py @args
        exit $LASTEXITCODE
    }
    "test" {
        & $PythonPath -m pytest -q
        exit $LASTEXITCODE
    }
}
