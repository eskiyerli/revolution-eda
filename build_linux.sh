#!/usr/bin/env bash
# Linux build script for Revolution EDA
# Builds standalone binaries for Python 3.12, 3.13, and 3.14 using Poetry virtual environments
# Runs inside the ubuntu_22_04 distrobox container (also used for AppImage packaging) so the
# binaries link against an older, widely-compatible glibc.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="reveda"
ENTRY_POINT="${SCRIPT_DIR}/reveda.py"
CONTAINER_NAME="${REVEDA_BUILD_CONTAINER:-ubuntu_22_04}"

# Re-execute inside the distrobox build container when invoked on the host (or another container)
if [[ "${CONTAINER_ID:-}" != "${CONTAINER_NAME}" && "${REVEDA_IN_BUILD_CONTAINER:-}" != "1" ]]; then
    if ! command -v distrobox >/dev/null 2>&1; then
        echo "ERROR: distrobox not found; run this script inside '${CONTAINER_NAME}' manually." >&2
        exit 1
    fi
    echo "Entering distrobox container '${CONTAINER_NAME}' for the build..."
    ENTER_ENV=(REVEDA_IN_BUILD_CONTAINER=1)
    if [[ -n "${POETRY_VENV_BASE:-}" ]]; then
        ENTER_ENV+=("POETRY_VENV_BASE=${POETRY_VENV_BASE}")
    fi
    exec distrobox enter "${CONTAINER_NAME}" -- env "${ENTER_ENV[@]}" \
        bash "${SCRIPT_DIR}/build_linux.sh" "$@"
fi

if ! command -v poetry >/dev/null 2>&1; then
    echo "ERROR: 'poetry' not found inside '${CONTAINER_NAME}'. Install it in the container first." >&2
    exit 1
fi

# Nuitka standalone mode needs a C toolchain and patchelf inside the container
for TOOL in gcc g++ patchelf; do
    if ! command -v "${TOOL}" >/dev/null 2>&1; then
        echo "ERROR: '${TOOL}' not found inside '${CONTAINER_NAME}'." >&2
        echo "Install it with: distrobox enter ${CONTAINER_NAME} -- sudo apt-get install -y build-essential patchelf ccache" >&2
        exit 1
    fi
done

# Change directory to the script/project root so relative Nuitka paths (like docs) are resolved correctly
cd "${SCRIPT_DIR}"

VENV_BASE="${POETRY_VENV_BASE:-${HOME}/.poetryenvs}"
OUTPUT_BASE="${HOME}/dist"

# Fail the build if the private revedaLicense module leaked into output
assert_no_bundled_license() {
    local report_path="$1"
    local dist_path="$2"

    if [[ ! -f "${report_path}" ]]; then
        echo "ERROR: Nuitka report not found: ${report_path}" >&2
        exit 1
    fi
    if grep -qE '<module[^>]*name="revedaLicense(\.|")' "${report_path}"; then
        echo "ERROR: Private license module included in Nuitka report:" >&2
        grep -oE 'name="revedaLicense[^"]*"' "${report_path}" | sort -u >&2
        exit 1
    fi
    local leaked
    leaked="$(find "${dist_path}" -name 'revedaLicense' -o -name 'revedaLicense.*')"
    if [[ -n "${leaked}" ]]; then
        echo "ERROR: Private license module found in build output:" >&2
        echo "${leaked}" >&2
        exit 1
    fi
}

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

    # Host-built venvs link against the host glibc and cannot run inside the container
    if ! "${PYTHON_PATH}" --version > /dev/null 2>&1; then
        echo "WARNING: ${PYTHON_PATH} fails to run in '${CONTAINER_NAME}' (built for the host glibc?) -- skipping"
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

    BUILD_REPORT="${OUTPUT_DIR}/nuitka-report.xml"

    # Build with Nuitka (most options come from nuitka-project directives in reveda.py)
    # Only specify overrides and platform-specific flags here
    echo "Building with Nuitka (this may take 10-30 minutes)..."
    "${PYTHON_PATH}" -m nuitka \
        --output-dir="${OUTPUT_DIR}" \
        --report="${BUILD_REPORT}" \
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

    assert_no_bundled_license "${BUILD_REPORT}" "${FINAL_FOLDER}"

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
