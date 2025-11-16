#!/bin/bash

# Astro Planner Setup Script
# This script sets up the development environment for the Astro Planner application

set -e  # Exit on error

echo "================================"
echo "Astro Planner Setup"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file from .env.example..."
    cp backend/.env.example backend/.env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and add your OpenWeatherMap API key"
    echo "   Get a free API key at: https://openweathermap.org/api"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Create data directory
echo "Creating data directory..."
mkdir -p data
echo "✓ Data directory created"
echo ""

echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "To start the application:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run the server:"
echo "     cd backend"
echo "     python -m uvicorn app.main:app --reload"
echo ""
echo "  3. Open your browser to:"
echo "     http://localhost:9247"
echo ""
echo "Alternatively, use Docker:"
echo "  docker-compose up -d"
echo ""
