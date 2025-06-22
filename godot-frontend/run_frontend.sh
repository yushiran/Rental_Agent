#!/bin/bash

# Script to run the Godot frontend for the Rental Agent system
echo "Starting Rental Agent Godot Frontend..."

# Check if Godot is installed
if command -v godot4 &> /dev/null; then
    GODOT_CMD="godot4"
elif command -v godot &> /dev/null; then
    GODOT_CMD="godot"
else
    echo "Error: Godot not found. Please install Godot 4.x."
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

# Run the Godot project
echo "Launching Godot project..."
$GODOT_CMD --path "$(dirname "$0")" "$@"
