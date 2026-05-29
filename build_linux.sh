#!/usr/bin/env bash
# Linux build script for Revolution EDA
# Builds standalone binaries for Python 3.12, 3.13, and 3.14 using Poetry virtual environments

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="reveda"
ENTRY_POINT="${SCRIPT_DIR}/reveda.py"

VENV_BASE="${POETRY_VENV_BASE:-${HOME}/.poetryenvs}"
OUTPUT_BASE="${HOME}/dist"

for PY_VER in 3.12 3.13 3.14; do
    ARTIFACT_NAME="linux-amd64-py${PY_VER}"
    echo "========================================"
    echo "Building Revolution EDA for Linux with Python ${PY_VER}"
    echo "========================================"

    # Find Poetry virtual environment
    MATCHED_DIR=$(find "${VENV_BASE}" -maxdepth 1 -type d -name "*py${PY_VER}" 2>/dev/null | head -n1)

    if [[ -z "${MATCHED_DIR}" ]]; then
        echo "WARNING: Poetry env for Python ${PY_VER} not found in ${VENV_BASE} -- skipping"
        continue
    fi

    PYTHON_PATH="${MATCHED_DIR}/bin/python"
    if [[ ! -x "${PYTHON_PATH}" ]]; then
        echo "WARNING: python not found in ${MATCHED_DIR} -- skipping"
        continue
    fi

    echo "Using Python: ${PYTHON_PATH}"

    # Ensure nuitka and key dependencies are installed
    echo "Installing/upgrading build dependencies..."
    "${PYTHON_PATH}" -m pip install --upgrade pip > /dev/null
    "${PYTHON_PATH}" -m pip install --upgrade nuitka > /dev/null

    # Output directory per Python version
    OUTPUT_DIR="${OUTPUT_BASE}/revolution-eda/${ARTIFACT_NAME}"
    if [[ -d "${OUTPUT_DIR}" ]]; then
        echo "Cleaning previous build..."
        rm -rf "${OUTPUT_DIR}"
    fi
    mkdir -p "${OUTPUT_DIR}"

    # Build with Nuitka (options match the nuitka-project directives in reveda.py)
    echo "Building with Nuitka (this may take 10-30 minutes)..."
    "${PYTHON_PATH}" -m nuitka \
        --standalone \
        --deployment \
        --enable-plugin=pyside6 \
        --enable-plugin=data-files \
        --include-data-dir=docs=docs \
        --include-package=revedaEditor \
        --include-package=cryptography \
        --include-package=markdown \
        --include-package=polars \
        --include-module=pydoc \
        --include-package=cProfile \
        --include-package=profile \
        --include-package=xml \
        --include-package=certifi \
        --include-module=PySide6.QtWebEngineWidgets \
        --include-module=PySide6.QtOpenGL \
        --nofollow-import-to=unittest \
        --nofollow-import-to=pytest \
        --nofollow-import-to=revedasim \
        --nofollow-import-to=revedaPlot \
        --nofollow-import-to=plugins \
        --nofollow-import-to=defaultPDK \
        --include-package-data=defaultPDK \
        --output-dir="${OUTPUT_DIR}" \
        --product-name="Revolution EDA" \
        --product-version="0.8.11" \
        --company-name="Revolution EDA" \
        --file-description="Electronic Design Automation Software for Professional Custom IC Design Engineers" \
        --copyright="Revolution Semiconductor (C) 2026" \
        --assume-yes-for-downloads \
        --jobs=2 \
        --lto=no \
        "${ENTRY_POINT}"

    # Move .dist contents to final location
    DIST_FOLDER="${OUTPUT_DIR}/${PROJECT_NAME}.dist"
    FINAL_FOLDER="${OUTPUT_DIR}/${PROJECT_NAME}"
    if [[ -d "${DIST_FOLDER}" ]]; then
        echo "Organizing build output..."
        mv "${DIST_FOLDER}" "${FINAL_FOLDER}"
    fi

    # Copy defaultPDK as data (excluded from compilation but included as package-data)
    PDK_SRC="${SCRIPT_DIR}/defaultPDK"
    PDK_DST="${FINAL_FOLDER}/defaultPDK"
    if [[ -d "${PDK_SRC}" && ! -d "${PDK_DST}" ]]; then
        echo "Copying defaultPDK..."
        cp -r "${PDK_SRC}" "${PDK_DST}"
    fi

    # Copy .env.example for reference
    ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
    if [[ -f "${ENV_EXAMPLE}" ]]; then
        cp "${ENV_EXAMPLE}" "${FINAL_FOLDER}/"
    fi

    # Clean up build artifacts
    echo "Cleaning up build artifacts..."
    BUILD_FOLDER="${OUTPUT_DIR}/${PROJECT_NAME}.build"
    if [[ -d "${BUILD_FOLDER}" ]]; then
        rm -rf "${BUILD_FOLDER}"
    fi

    # Create tar.gz artifact
    echo "Creating tar.gz artifact..."
    TAR_NAME="${OUTPUT_BASE}/revolution-eda/${ARTIFACT_NAME}.tar.gz"
    tar -czf "${TAR_NAME}" -C "${OUTPUT_DIR}" "${PROJECT_NAME}"

    echo "Build completed! Artifact: ${TAR_NAME}"
    echo ""
done

echo "All builds completed."
