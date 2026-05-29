#!/bin/bash

# Procurement Chatbot - Quick Start Guide
# ======================================

echo "Procurement Chatbot - Starting Server"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv .venv
    echo "Virtual environment created"
fi

# Activate virtual environment
source .venv/bin/activate
echo "Virtual environment activated"

# Install/update requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null
echo "Dependencies installed"

echo "Open http://localhost:8952 in your browser."

echo "Press Ctrl+C to stop the server"

# Start the chatbot server (use 'python' from venv, not 'python3')
python chatbot.py
