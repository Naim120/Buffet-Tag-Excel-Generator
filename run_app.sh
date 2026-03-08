#!/bin/bash
cd "$(dirname "$0")"

# Check if venv exists, if not create it
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Check if packages are installed, if not try install (fast check)
if ! pip freeze | grep -q "gunicorn"; then
     echo "Installing dependencies..."
     pip install -r requirements.txt
fi

# Run the Flask app with Gunicorn (Production)
echo "Starting Web Server (Gunicorn)..."
# -w 4: 4 worker processes
# -b 0.0.0.0:5050: Bind to all interfaces on port 5050
exec gunicorn -w 4 -b 0.0.0.0:5050 app:app
