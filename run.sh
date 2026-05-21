#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🌌 Initializing Antigravity Deep Research Agent Setup..."

# 1. Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.9+ to continue."
    exit 1
fi

# 2. Setup Virtual Environment (Optional but highly recommended)
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
echo "⬇️ Installing required packages from requirements.txt..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 4. Launch Streamlit UI Dashboard
echo "🟢 Launching visual UI Dashboard in headless mode..."
streamlit run app.py --server.port 8501 --server.headless true
