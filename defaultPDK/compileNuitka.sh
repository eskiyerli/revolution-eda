#!/bin/bash
for py in python3.12 python3.13 python3.14; do
    if command -v "$py" &> /dev/null; then
        echo "Building defaultPDK with Poetry env ($py)..."
        poetry env use "$py"
        poetry run python -m nuitka --module defaultPDK --include-package=defaultPDK --output-dir="$HOME/dist/defaultPDK/$py"
    else
        echo "Skipping $py (not found)"
    fi
done
