#!/bin/bash
# Setup script for Recursive://Neon (Linux/Mac)

set -e

echo "=========================================="
echo "Recursive://Neon - Setup Script"
echo "=========================================="
echo

# Check Python version
echo "[1/6] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION found"
echo

# Setup Python backend
echo "[2/6] Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

cd ..
echo "✓ Backend setup complete"
echo

# Setup Node.js frontend
echo "[3/6] Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✓ Node.js $NODE_VERSION found"
echo

echo "[4/6] Setting up frontend..."
cd frontend
npm install
cd ..
echo "✓ Frontend setup complete"
echo

# Download ollama
echo "[5/6] Downloading ollama..."
python3 scripts/download_ollama.py
echo "✓ Ollama downloaded"
echo

# Download default model (optional, commented out for now)
# echo "[6/6] Downloading default model..."
# echo "Skipping model download (do this manually if needed)"
echo "[6/6] Setup complete!"
echo

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "To run the game:"
echo "  1. Start backend:  cd backend && source venv/bin/activate && python -m backend.main"
echo "  2. Start frontend: cd frontend && npm run dev"
echo "  3. Open browser:   http://localhost:5173"
echo
echo "Note: You need to have a compatible model in ollama."
echo "Run: ollama pull phi3:mini"
echo
