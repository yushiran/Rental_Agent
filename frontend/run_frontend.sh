#!/bin/bash

# Script to run the Phaser frontend for the Rental Agent system
echo "Starting Rental Agent Phaser Frontend..."

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Check if backend server is running
echo "Checking if backend server is running on localhost:8000..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "Backend server detected."
else
    echo "Warning: Backend server not detected at http://localhost:8000/"
    echo "Make sure to start the backend server before using the frontend."
fi

# Go to the phaser-frontend directory
cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run the development server using npm
echo "Starting npm development server..."
echo "Frontend will be available at: http://localhost:5173"

# Run the development server
npm run dev

# Note: npm run dev will block the terminal until manually stopped with Ctrl+C
