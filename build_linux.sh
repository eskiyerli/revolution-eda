#!/usr/bin/env bash
# Linux build script for Revolution EDA
# Builds standalone binaries for Python 3.12, 3.13, and 3.14 using Poetry virtual environments

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="reveda"
ENTRY_POINT="${SCRIPT_DIR}/reveda.py"

# Change directory to the script/project root so relative Nuitka paths (like docs) are resolved correctly
cd "${SCRIPT_DIR}"

VENV_BASE="${POETRY_VENV_BASE:-${HOME}/.poetryenvs}"
OUTPUT_BASE="${HOME}/dist"

# for PY_VER in 3.12 3.13 3.14; do
for PY_VER in 3.13; do
    # ARTIFACT_NAME="linux-amd64-py${PY_VER}"
    ARTIFACT_NAME="linux-amd64"
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
    "${PYTHON_PATH}" -m pip install -r <(poetry export -f requirements.txt) > /dev/null

    # Output directory per Python version
    OUTPUT_DIR="${OUTPUT_BASE}/revolution-eda/${ARTIFACT_NAME}"
    if [[ -d "${OUTPUT_DIR}" ]]; then
        echo "Cleaning previous build..."
        rm -rf "${OUTPUT_DIR}"
    fi
    mkdir -p "${OUTPUT_DIR}"

    # Build with Nuitka (most options come from nuitka-project directives in reveda.py)
    # Only specify overrides and platform-specific flags here
    echo "Building with Nuitka (this may take 10-30 minutes)..."
    "${PYTHON_PATH}" -m nuitka \
        --output-dir="${OUTPUT_DIR}" \
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

    # Build defaultPDK as a separate compiled module
    PDK_SRC="${SCRIPT_DIR}/defaultPDK"
    PDK_DST="${FINAL_FOLDER}/defaultPDK"
    PDK_BUILD_DIR="${OUTPUT_DIR}/defaultPDK_build"
    if [[ -d "${PDK_SRC}" ]]; then
        echo "Building defaultPDK as a compiled module..."
        mkdir -p "${PDK_BUILD_DIR}"
        "${PYTHON_PATH}" -m nuitka \
            --module \
            --include-package=defaultPDK \
            --output-dir="${PDK_BUILD_DIR}" \
            --assume-yes-for-downloads \
            --jobs=2 \
            --lto=no \
            defaultPDK

        # Copy compiled .so into the final folder
        find "${PDK_BUILD_DIR}" -name "defaultPDK*.so" -exec cp {} "${FINAL_FOLDER}/" \;

        # Copy data files (stipples/, config.json) that the PDK needs at runtime
        mkdir -p "${PDK_DST}"
        cp -r "${PDK_SRC}/stipples" "${PDK_DST}/" 2>/dev/null || true
        cp "${PDK_SRC}/config.json" "${PDK_DST}/" 2>/dev/null || true

        # Clean up PDK build artifacts
        rm -rf "${PDK_BUILD_DIR}"
    fi

    # Copy .env.example for reference and project auto-initialization
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
