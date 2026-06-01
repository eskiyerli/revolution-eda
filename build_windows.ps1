# Windows build script for Revolution EDA
# Builds standalone binaries for Python 3.12, 3.13, and 3.14 using Poetry virtual environments

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectName = "reveda"
$EntryPoint = Join-Path $ScriptDir "reveda.py"

$VenvBase = if ($env:POETRY_VENV_BASE) { $env:POETRY_VENV_BASE } else { "C:\Users\eskiye50\poetryenvs" }
$OutputBase = "C:\Users\eskiye50\dist"

foreach ($PyVer in @("3.12", "3.13", "3.14")) {
    $ArtifactName = "windows-amd64-py${PyVer}"
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Building Revolution EDA for Windows with Python $PyVer" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Find Poetry virtual environment
    $Pattern = Join-Path $VenvBase "*py$PyVer"
    $MatchedDirs = Get-ChildItem -Directory -Path $Pattern -ErrorAction SilentlyContinue

    if (-not $MatchedDirs) {
        Write-Warning "Poetry env for Python $PyVer not found in $VenvBase -- skipping"
        continue
    }

    $PythonPath = Join-Path $MatchedDirs[0].FullName "Scripts\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Warning "python.exe not found in $($MatchedDirs[0].FullName) -- skipping"
        continue
    }

    Write-Host "Using Python: $PythonPath"

    # Ensure nuitka and key dependencies are installed
    Write-Host "Installing/upgrading build dependencies..."
    & $PythonPath -m pip install --upgrade pip | Out-Null
    & $PythonPath -m pip install --upgrade nuitka | Out-Null

    # Output directory per Python version
    $OutputDir = Join-Path $OutputBase "revolution-eda\$ArtifactName"
    if (Test-Path $OutputDir) {
        Write-Host "Cleaning previous build..."
        Remove-Item -Recurse -Force $OutputDir
    }
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    # Build with Nuitka (most options come from nuitka-project directives in reveda.py)
    # Only specify overrides and platform-specific flags here
    Write-Host "Building with Nuitka (this may take 10-30 minutes)..."
    & $PythonPath -m nuitka `
        --msvc=latest `
        --output-dir=$OutputDir `
        --assume-yes-for-downloads `
        --jobs=2 `
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

    # Compile defaultPDK as a separate .pyd package
    Write-Host "Compiling defaultPDK as separate package..."
    $PdkSrc = Join-Path $ScriptDir "defaultPDK"
    $PdkBuildDir = Join-Path $OutputDir "defaultPDK_build"
    New-Item -ItemType Directory -Force -Path $PdkBuildDir | Out-Null

    & $PythonPath -m nuitka `
        --mode=package `
        --msvc=latest `
        --include-package=defaultPDK `
        --output-dir=$PdkBuildDir `
        --assume-yes-for-downloads `
        --no-pyi-file `
        --jobs=2 `
        --lto=no `
        $PdkSrc

    if ($LASTEXITCODE -eq 0) {
        # Copy compiled defaultPDK into the artifact
        $PdkDistFolder = Join-Path $PdkBuildDir "defaultPDK.dist"
        $PdkTargetFolder = Join-Path $FinalFolder "defaultPDK"
        if (Test-Path $PdkDistFolder) {
            if (Test-Path $PdkTargetFolder) { Remove-Item -Recurse -Force $PdkTargetFolder }
            Copy-Item -Path $PdkDistFolder -Destination $PdkTargetFolder -Recurse -Force
        } else {
            # Nuitka may output directly without .dist for package mode
            $PdkCompiledFolder = Join-Path $PdkBuildDir "defaultPDK"
            if (Test-Path $PdkCompiledFolder) {
                if (Test-Path $PdkTargetFolder) { Remove-Item -Recurse -Force $PdkTargetFolder }
                Copy-Item -Path $PdkCompiledFolder -Destination $PdkTargetFolder -Recurse -Force
            }
        }
        Write-Host "defaultPDK compiled successfully." -ForegroundColor Green
    } else {
        Write-Warning "defaultPDK compilation failed -- falling back to source copy"
    }

    # Ensure defaultPDK exists (fallback: copy source modules including stipples)
    $PdkDst = Join-Path $FinalFolder "defaultPDK"
    if (-not (Test-Path $PdkDst)) {
        Write-Host "Copying defaultPDK source modules..."
        Copy-Item -Path $PdkSrc -Destination $PdkDst -Recurse -Force
    }
    # Always copy stipples and data files that Nuitka may miss
    $StipplesSrc = Join-Path $PdkSrc "stipples"
    $StipplesDst = Join-Path $PdkDst "stipples"
    if ((Test-Path $StipplesSrc) -and -not (Test-Path $StipplesDst)) {
        Copy-Item -Path $StipplesSrc -Destination $StipplesDst -Recurse -Force
    }

    # Clean up defaultPDK build artifacts
    if (Test-Path $PdkBuildDir) { Remove-Item -Recurse -Force $PdkBuildDir }

    # Copy .env.example for reference
    $EnvExample = Join-Path $ScriptDir ".env.example"
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample -Destination $FinalFolder -Force
    }

    # Clean up build artifacts
    Write-Host "Cleaning up build artifacts..."
    $BuildFolder = Join-Path $OutputDir "$ProjectName.build"
    if (Test-Path $BuildFolder) { Remove-Item -Recurse -Force $BuildFolder }

    # Create zip artifact
    Write-Host "Creating zip artifact..."
    $ZipName = Join-Path $OutputBase "revolution-eda\${ArtifactName}.zip"
    Compress-Archive -Path "$FinalFolder\*" -DestinationPath $ZipName -Force

    Write-Host "Build completed! Artifact: $ZipName" -ForegroundColor Green
    Write-Host ""
}

Write-Host "All builds completed." -ForegroundColor Green
