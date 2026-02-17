#!/bin/bash
cd "$(dirname "$0")"

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
    # Check if packages are installed, if not try install (fast check)
    if ! pip freeze | grep -q "Flask"; then
         echo "Installing dependencies..."
         pip install -r requirements.txt
    fi
fi

# Run the Flask app
echo "Starting Web Server..."
python3 app.py
