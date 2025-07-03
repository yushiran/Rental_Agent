#!/bin/bash

# Script to start both backend and frontend development servers
# This script will open two terminal windows/tabs

echo "Starting Rental Agent Development Environment..."

# Get the current directory (project root)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to open a new terminal with command
open_terminal_with_command() {
    local dir="$1"
    local command="$2"
    local title="$3"
    
    # Try different terminal emulators
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$title" --working-directory="$dir" -- bash -c "$command; exec bash"
    elif command -v konsole &> /dev/null; then
        konsole --new-tab --title="$title" --workdir="$dir" -e bash -c "$command; exec bash"
    elif command -v xfce4-terminal &> /dev/null; then
        xfce4-terminal --title="$title" --working-directory="$dir" -e "bash -c '$command; exec bash'"
    elif command -v xterm &> /dev/null; then
        xterm -title "$title" -e "cd '$dir' && $command; exec bash" &
    else
        echo "No supported terminal emulator found. Please run the commands manually:"
        echo "Terminal 1: cd $dir && $command"
    fi
}

# Start backend server
echo "Starting backend server..."
open_terminal_with_command "$PROJECT_ROOT/backend" "fastapi run app/api_service/main.py" "Backend Server"

# Wait a moment before starting frontend
sleep 2

# Start frontend server
echo "Starting frontend server..."
open_terminal_with_command "$PROJECT_ROOT/frontend" "source ~/.nvm/nvm.sh && nvm use 18 && npm run dev" "Frontend Server"

echo "Development servers starting..."
echo "Backend will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:5173"
echo ""
echo "Press Ctrl+C in each terminal to stop the servers"
