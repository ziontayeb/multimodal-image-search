#!/bin/bash

# Image Search Web UI Startup Script

echo "================================"
echo "Image Search Web UI"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found!"
    echo "Please run this script from the web/ directory"
    exit 1
fi

# Check for .env file
if [ ! -f "../.env" ]; then
    echo "Warning: .env file not found in project root!"
    echo "You'll need to configure API keys in the Settings page."
    echo ""
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Flask not installed!"
    echo "Please run: pip install -r ../requirements.txt"
    exit 1
fi

echo "Starting server..."
echo ""
echo "Web UI will be available at:"
echo "  http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Flask app
python3 app.py
