# Windows build script for Revolution EDA
# Builds a standalone binary using a Poetry virtual environment.
# Most Nuitka options come from nuitka-project directives in reveda.py;
# this script only adds platform-specific flags.
#
# Usage:
#   .\build_windows.ps1                          # default: Python 3.14 + zip
#   .\build_windows.ps1 -PythonVersions 3.13,3.14
#   .\build_windows.ps1 -VenvDir C:\path\to\venv # explicit Poetry venv
#   .\build_windows.ps1 -SkipZip                 # dist folder only (for Inno Setup)

param(
    [string[]]$PythonVersions = @("3.13"),
    [string]$VenvDir = $env:POETRY_VENV,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectName = "reveda"
$EntryPoint = Join-Path $ScriptDir "reveda.py"

# Pinned for reproducible builds; bump deliberately.
$NuitkaVersion = "4.2.2"

$VenvBase = if ($env:POETRY_VENV_BASE) { $env:POETRY_VENV_BASE } else { "C:\Users\eskiye50\poetryenvs" }
$OutputBase = "C:\Users\eskiye50\dist"
$Jobs = if ($env:NUITKA_JOBS) { [int]$env:NUITKA_JOBS } else { [Environment]::ProcessorCount }

foreach ($PyVer in $PythonVersions) {
    $ArtifactName = "windows-amd64-py${PyVer}"
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Building Revolution EDA for Windows with Python $PyVer" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Find Poetry virtual environment
    if ($VenvDir) {
        $MatchedDirs = @(Get-Item -Path $VenvDir -ErrorAction SilentlyContinue)
    } else {
        $Pattern = Join-Path $VenvBase "*py$PyVer"
        $MatchedDirs = Get-ChildItem -Directory -Path $Pattern -ErrorAction SilentlyContinue |
            Sort-Object Name
    }

    if (-not $MatchedDirs) {
        $Where = if ($VenvDir) { $VenvDir } else { $Pattern }
        Write-Warning "Poetry env for Python $PyVer not found at $Where -- skipping"
        continue
    }
    if ($MatchedDirs.Count -gt 1) {
        $Msg = "Multiple Poetry envs match Python ${PyVer}; using $($MatchedDirs[0].Name). " +
            "Pass -VenvDir or set POETRY_VENV to select a different one."
        Write-Warning $Msg
    }

    $PythonPath = Join-Path $MatchedDirs[0].FullName "Scripts\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Warning "python.exe not found in $($MatchedDirs[0].FullName) -- skipping"
        continue
    }

    Write-Host "Using Python: $PythonPath"

    # Ensure a pinned nuitka is installed
    Write-Host "Installing build dependencies (nuitka==$NuitkaVersion)..."
    & $PythonPath -m pip install --upgrade pip | Out-Null
    & $PythonPath -m pip install "nuitka==$NuitkaVersion" | Out-Null

    # Output directory per Python version
    $OutputDir = Join-Path $OutputBase "revolution-eda\$ArtifactName"
    if (Test-Path $OutputDir) {
        Write-Host "Cleaning previous build..."
        Remove-Item -Recurse -Force $OutputDir
    }
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    # Build with Nuitka (most options come from nuitka-project directives in reveda.py)
    # Only specify overrides and platform-specific flags here
    Write-Host "Building with Nuitka $NuitkaVersion (this may take 10-30 minutes)..."
    & $PythonPath -m nuitka `
        --msvc=latest `
        --output-dir=$OutputDir `
        --assume-yes-for-downloads `
        --jobs=$Jobs `
        --lto=no `
        $EntryPoint

    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka build failed for Python $PyVer"
    }

    # Move .dist contents to final location
    $DistFolder = Join-Path $OutputDir "$ProjectName.dist"
    $FinalFolder = Join-Path $OutputDir $ProjectName
    if (Test-Path $DistFolder) {
        Write-Host "Organizing build output..."
        Rename-Item -Path $DistFolder -NewName $ProjectName
    }

    # Ensure defaultPDK runtime data exists on disk next to the executable.
    # The PDK code itself is embedded via --include-package=defaultPDK in
    # reveda.py, but layer stipple textures and config.json are looked up
    # through filesystem paths relative to the package/REVEDA_PDK_PATH.
    $PdkSrc = Join-Path $ScriptDir "defaultPDK"
    $PdkDst = Join-Path $FinalFolder "defaultPDK"
    foreach ($Item in @("config.json", "stipples")) {
        $Src = Join-Path $PdkSrc $Item
        $Dst = Join-Path $PdkDst $Item
        if ((Test-Path $Src) -and -not (Test-Path $Dst)) {
            New-Item -ItemType Directory -Force -Path $PdkDst | Out-Null
            Copy-Item -Path $Src -Destination $Dst -Recurse -Force
        }
    }

    # Copy .env.example for reference
    $EnvExample = Join-Path $ScriptDir ".env.example"
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample -Destination $FinalFolder -Force
    }

    # Clean up build artifacts
    Write-Host "Cleaning up build artifacts..."
    $BuildFolder = Join-Path $OutputDir "$ProjectName.build"
    if (Test-Path $BuildFolder) { Remove-Item -Recurse -Force $BuildFolder }

    if (-not $SkipZip) {
        # Create zip artifact
        Write-Host "Creating zip artifact..."
        $ZipName = Join-Path $OutputBase "revolution-eda\${ArtifactName}.zip"
        Compress-Archive -Path "$FinalFolder\*" -DestinationPath $ZipName -Force
        Write-Host "Build completed! Artifact: $ZipName" -ForegroundColor Green
    } else {
        Write-Host "Build completed! Dist folder: $FinalFolder" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "All builds completed." -ForegroundColor Green
