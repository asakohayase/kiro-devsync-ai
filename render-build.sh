#!/bin/bash
set -e

echo "=== Render Build Script ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Current PATH: $PATH"

# Remove any conflicting uv installations and Rust toolchain
echo "Cleaning up potential conflicts..."
rm -rf ~/.cargo/bin/uv* 2>/dev/null || true
rm -rf ~/.local/bin/uv* 2>/dev/null || true
rm -rf ~/.cargo 2>/dev/null || true
rm -rf ~/.rustup 2>/dev/null || true

# Clean PATH of any uv/cargo/rust references
echo "Cleaning PATH..."
CLEAN_PATH=""
IFS=':' read -ra PATH_ARRAY <<< "$PATH"
for dir in "${PATH_ARRAY[@]}"; do
    if [[ ! "$dir" =~ (uv|cargo|rust) ]]; then
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
else
    echo "ERROR: No Python interpreter found!"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo "Using Pip: $PIP_CMD"

# Upgrade pip first
echo "Upgrading pip..."
$PIP_CMD install --upgrade pip

# Install dependencies with strict binary-only policy to prevent compilation
echo "Installing dependencies with binary-only policy..."
$PIP_CMD install --no-cache-dir \
    --only-binary=:all: \
    --prefer-binary \
    --no-compile \
    -r requirements.txt

echo "=== Build Complete ==="