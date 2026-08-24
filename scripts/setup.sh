#!/bin/bash
# ASA — One-command demo setup
set -e

echo "=== ASA Setup ==="

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $python_version"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -e ".[dev]" 2>/dev/null || pip install -e ".[dev]"

# Create data directory
mkdir -p data/repos data/cache data/exports

# Install frontend dependencies (if Node.js available)
if command -v node &> /dev/null; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install 2>/dev/null && cd ..
else
    echo "Node.js not found — skipping frontend installation"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  asa analyze https://github.com/example/project"
echo "  asa serve"
echo "  asa status"
