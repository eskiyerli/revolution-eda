# Build the machine-fingerprint utility as a single-file Nuitka executable (Windows)
# Output: dist/machineFingerprint/reveda-machine-fingerprint.exe
#
# The resulting .exe is fully self-contained: customers need no Python,
# Revolution EDA, or any third-party package to read their machine fingerprint.
#
# Usage:
#     .\scripts\build_fingerprint_exe.ps1
#
# By default this uses the Python on PATH. To build against a specific Poetry
# env (recommended: Python 3.13, which Nuitka fully supports), pass -PythonPath:
#     .\scripts\build_fingerprint_exe.ps1 -PythonPath C:\path\to\python.exe

param(
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

# Resolve the Python interpreter to build with.
if (-not $PythonPath) {
    # Prefer a Python 3.13 Poetry env when available (Nuitka fully supports it),
    # matching the convention used by revedaLicense\build_nuitka.ps1.
    $VenvBase = if ($env:POETRY_VENV_BASE) { $env:POETRY_VENV_BASE } else { "C:\Users\eskiye50\poetryenvs" }
    $Pattern = Join-Path $VenvBase "*py3.13"
    $MatchedDirs = Get-ChildItem -Directory -Path $Pattern -ErrorAction SilentlyContinue

    if ($MatchedDirs) {
        $Candidate = Join-Path $MatchedDirs[0].FullName "Scripts\python.exe"
        if (Test-Path $Candidate) {
            $PythonPath = $Candidate
        }
    }

    if (-not $PythonPath) {
        Write-Warning "No Python 3.13 Poetry env found in $VenvBase -- falling back to 'python' on PATH."
        $PythonPath = "python"
    }
}

$SourceScript = Join-Path $ScriptDir "machine_fingerprint.py"
if (-not (Test-Path $SourceScript)) {
    throw "Source script not found: $SourceScript"
}

$OutputDir = Join-Path $ProjectRoot "dist\machineFingerprint"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "Building reveda-machine-fingerprint.exe with: $PythonPath"

& $PythonPath -m nuitka `
    --onefile `
    --assume-yes-for-downloads `
    --msvc=latest `
    --output-dir=$OutputDir `
    --output-filename=reveda-machine-fingerprint.exe `
    $SourceScript

if ($LASTEXITCODE -ne 0) {
    throw "Nuitka build failed (exit code $LASTEXITCODE)"
}

# Remove intermediate build artifacts, keeping only the final executable.
Remove-Item -Recurse -Force `
    (Join-Path $OutputDir "machine_fingerprint.build"), `
    (Join-Path $OutputDir "machine_fingerprint.dist"), `
    (Join-Path $OutputDir "machine_fingerprint.onefile-build") `
    -ErrorAction SilentlyContinue

$Exe = Join-Path $OutputDir "reveda-machine-fingerprint.exe"
Write-Host ""
Write-Host "Build complete: $Exe"
