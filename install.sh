#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Alfred MCP Server — 1-Click Installer   "
echo "=========================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "ℹ️  Found Python $PYTHON_VERSION"

# Setup virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# Ensure pip is installed inside venv
if ! .venv/bin/python -m pip --version &> /dev/null; then
    echo "🔧 Bootstrapping pip in virtual environment..."
    .venv/bin/python -m ensurepip --default-pip || true
fi

# Install dependencies
echo "📥 Installing required packages..."
.venv/bin/python -m pip install -q -r requirements.txt

# Run server installer to update client configs
echo "⚙️  Configuring MCP Client..."
.venv/bin/python server.py --install

echo "=========================================="
echo "✅ Setup complete! You are ready to go."
echo "=========================================="
