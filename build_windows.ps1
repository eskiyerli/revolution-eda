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

    # Build with Nuitka (options match the nuitka-project directives in reveda.py)
    Write-Host "Building with Nuitka (this may take 10-30 minutes)..."
    & $PythonPath -m nuitka `
        --standalone `
        --deployment `
        --msvc=latest `
        --enable-plugin=pyside6 `
        --enable-plugin=data-files `
        --include-data-dir=docs=docs `
        --include-package=revedaEditor `
        --include-package=cryptography `
        --include-package=markdown `
        --include-package=polars `
        --include-module=pydoc `
        --include-package=cProfile `
        --include-package=profile `
        --include-package=xml `
        --include-package=certifi `
        --include-module=PySide6.QtWebEngineWidgets `
        --include-module=PySide6.QtOpenGL `
        --nofollow-import-to=unittest `
        --nofollow-import-to=pytest `
        --nofollow-import-to=revedasim `
        --nofollow-import-to=revedaPlot `
        --nofollow-import-to=plugins `
        --nofollow-import-to=defaultPDK `
        --include-package-data=defaultPDK `
        --output-dir=$OutputDir `
        --product-name="Revolution EDA" `
        --product-version="0.8.11" `
        --company-name="Revolution EDA" `
        --file-description="Electronic Design Automation Software for Professional Custom IC Design Engineers" `
        --windows-icon-from-ico=revedaCoreLogo.ico `
        --copyright="Revolution Semiconductor (C) 2026" `
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

    # Copy defaultPDK as data (excluded from compilation but included as package-data)
    $PdkSrc = Join-Path $ScriptDir "defaultPDK"
    $PdkDst = Join-Path $FinalFolder "defaultPDK"
    if ((Test-Path $PdkSrc) -and -not (Test-Path $PdkDst)) {
        Write-Host "Copying defaultPDK..."
        Copy-Item -Path $PdkSrc -Destination $PdkDst -Recurse -Force
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

    # Create zip artifact
    Write-Host "Creating zip artifact..."
    $ZipName = Join-Path $OutputBase "revolution-eda\${ArtifactName}.zip"
    Compress-Archive -Path "$FinalFolder\*" -DestinationPath $ZipName -Force

    Write-Host "Build completed! Artifact: $ZipName" -ForegroundColor Green
    Write-Host ""
}

Write-Host "All builds completed." -ForegroundColor Green
