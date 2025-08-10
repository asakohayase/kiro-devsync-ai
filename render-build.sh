#!/bin/bash
set -e

echo "=== Render Build Script ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Current PATH: $PATH"

# Remove any conflicting uv installations
echo "Cleaning up potential uv conflicts..."
rm -rf ~/.cargo/bin/uv* 2>/dev/null || true
rm -rf ~/.local/bin/uv* 2>/dev/null || true

# Clean PATH of any uv references and rebuild it safely
echo "Cleaning PATH..."
CLEAN_PATH=""
IFS=':' read -ra PATH_ARRAY <<< "$PATH"
for dir in "${PATH_ARRAY[@]}"; do
    if [[ ! "$dir" =~ (uv|cargo) ]]; then
        if [ -z "$CLEAN_PATH" ]; then
            CLEAN_PATH="$dir"
        else
            CLEAN_PATH="$CLEAN_PATH:$dir"
        fi
    fi
done
export PATH="$CLEAN_PATH"

echo "Cleaned PATH: $PATH"

# Verify we can still access python and pip
echo "Verifying tools after PATH cleanup..."
PYTHON_CMD=""
PIP_CMD=""

# Try to find python and pip
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    PIP_CMD="python3 -m pip"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
    PIP_CMD="python -m pip"
elif command -v uv >/dev/null 2>&1; then
    echo "Using uv as fallback..."
    uv sync --frozen
    echo "=== Build Complete (using uv) ==="
    exit 0
else
    echo "ERROR: No Python interpreter found!"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo "Using Pip: $PIP_CMD"

# Install dependencies with pip, using binary packages where possible to avoid compilation issues
echo "Installing dependencies..."
$PIP_CMD install --no-cache-dir --only-binary=cryptography,bcrypt,pydantic -r requirements.txt

echo "=== Build Complete ==="