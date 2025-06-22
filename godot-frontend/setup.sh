#!/bin/bash

# Setup script for Rental Agent Godot Frontend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up Rental Agent Godot Frontend..."

# Check if Godot is already installed
if command -v godot4 &> /dev/null; then
    echo "Godot 4 is already installed as 'godot4'."
    GODOT_INSTALLED=true
elif command -v godot &> /dev/null && godot --version | grep -q "4."; then
    echo "Godot 4 is already installed as 'godot'."
    GODOT_INSTALLED=true
else
    GODOT_INSTALLED=false
    echo "Godot 4 not found. Attempting to install..."
    
    # Detect operating system
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        GODOT_VERSION="4.2.1"
        GODOT_DIR="$HOME/.local/share/godot"
        GODOT_BIN="$HOME/.local/bin"
        
        mkdir -p "$GODOT_DIR"
        mkdir -p "$GODOT_BIN"
        
        echo "Downloading Godot $GODOT_VERSION for Linux..."
        wget -q --show-progress "https://github.com/godotengine/godot/releases/download/$GODOT_VERSION-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip" -O /tmp/godot.zip
        
        echo "Extracting Godot..."
        unzip -q /tmp/godot.zip -d /tmp
        mv /tmp/Godot_v${GODOT_VERSION}-stable_linux.x86_64 "$GODOT_DIR/godot"
        
        # Create symbolic link
        ln -sf "$GODOT_DIR/godot" "$GODOT_BIN/godot"
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$GODOT_BIN:"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            echo "Added Godot to PATH. Please restart your terminal after this script completes."
        fi
        
        echo "Godot $GODOT_VERSION installed successfully. You may need to restart your terminal."
        GODOT_INSTALLED=true
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS installation
        if command -v brew &> /dev/null; then
            echo "Installing Godot via Homebrew..."
            brew install --cask godot
            GODOT_INSTALLED=true
        else
            echo "Homebrew not found. Please install Godot manually from https://godotengine.org/download"
            GODOT_INSTALLED=false
        fi
    else
        echo "Unsupported operating system. Please install Godot manually from https://godotengine.org/download"
        GODOT_INSTALLED=false
    fi
fi

# Verify installation
if [ "$GODOT_INSTALLED" = true ]; then
    echo "Godot installation verified. Continuing with setup..."
else
    echo "Warning: Godot installation could not be verified. Setup will continue, but you may need to install Godot manually."
    echo "Visit: https://godotengine.org/download"
fi

# Create base directories for assets
mkdir -p assets/tilesets
mkdir -p assets/characters
mkdir -p assets/ui

echo "Directory structure created successfully."
echo ""
echo "Next steps:"
echo "1. Add your pixel art assets to the assets directories"
echo "2. Ensure the backend server is running at http://localhost:8000"
echo "3. Run the Godot project by executing: ./run_frontend.sh"
echo ""

# Make run_frontend.sh executable
chmod +x ./run_frontend.sh

# Check if backend server is running
echo "Checking if backend server is running on localhost:8000..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "Backend server detected and ready."
else
    echo "Backend server not detected at http://localhost:8000/"
    echo "Make sure to start the backend server before running the frontend."
fi

echo "Setup complete! You can now run ./run_frontend.sh to start the Godot project."
