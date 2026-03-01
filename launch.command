#!/bin/bash
# Investment Tracker - Double-click to launch

# Change to the directory where this script lives
cd "$(dirname "$0")"

echo "=========================================="
echo "  Investment Tracker - Starting Up"
echo "=========================================="
echo ""

# Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
else
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3 from https://python.org"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (first run only)..."
    $PYTHON -m venv .venv
    echo ""
fi

# Activate virtual environment
source .venv/bin/activate

# Install/upgrade dependencies
echo "Checking dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "Dependencies OK."
echo ""

# Launch Streamlit
echo "Starting Investment Tracker..."
echo "The app will open in your browser shortly."
echo "To stop: close this window or press Ctrl+C."
echo ""
streamlit run app.py --server.headless=true --browser.gatherUsageStats=false

# Keep terminal open if Streamlit exits unexpectedly
read -p "Press Enter to exit..."
