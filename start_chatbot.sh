#!/bin/bash

# Procurement Chatbot - Quick Start Guide
# ======================================

echo "🚀 Procurement Chatbot - Starting Server"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Install/update requirements
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null
echo "✅ Dependencies installed"

echo ""
echo "=========================================="
echo "✅ Chatbot is starting..."
echo "=========================================="
echo ""
echo "📍 Server: http://localhost:8950"
echo "📚 API Docs: http://localhost:8950/docs"
echo "🔄 ReDoc: http://localhost:8950/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start the chatbot server (use 'python' from venv, not 'python3')
python chatbot.py
